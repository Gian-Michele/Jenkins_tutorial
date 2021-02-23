from kafka import KafkaConsumer
import json
import logging
import datetime
from controller.nats_interface import InstructiveInterface
from jsonschema import validate, SchemaError

# function to update the json to tx when a payload is received
def add_measurement_to_json(json_to_tx, payload_rx, ue_list):

    # data struct:
    ue_info_2_tx = {
        "pci": 111,
        "rnti": 0,
        "tmsi_flag": 1,
        "mmec": 10,
        "m-timsi": "timsi",
        "dlThroughput": 0,
        "ulThroughput": 0,
        "rsrp": 0,
        "wbCqi": 0,
        "wbRi": 0,
        "puschSnr": 0,
        "pucchSnr": 0,
        "dlMcs": 0,
        "ulMcs": 0,
        "numDlRbs": 0,
        "numUlRbs": 0,
        "maxDlRank": 0,
        "maxDlMcs": 0,
        "maxUlMcs": 0,
        "maxNumDlRbs": 0,
        "maxNumUlRbs": 0,
        "rlcBufferDl": 0,
        "rlcBufferUl": 0,
        "numNeighborDescriptors": 0,
        "neighborCells": []
    }

    # When is the serving Cell
    if payload_rx['ueMeasurement']['cellId'] == payload_rx['ueMeasurement']['ueCellId']:
        ue_id = payload_rx['ueMeasurement']['ueRicId'].split('_')[1]
        if ue_id not in ue_list:
            ue_list.append(int(ue_id))
            json_to_tx['numUeDescriptors'] = json_to_tx['numUeDescriptors'] + 1
            ue = ue_info_2_tx
            if payload_rx['ueMeasurement']['ueCellId'] == 152:
                ue['pci'] = 0
            else:
                ue['pci'] = 1
            ue['rsrp'] = payload_rx['ueMeasurement']['rsrp']
            ue['rnti'] = int(ue_id)
            ue['m-timsi'] = ue_id
            ue['mmec'] = int(ue_id)
            if 'ues' in json_to_tx:  # when more the 1 UE is in the network
                json_to_tx['ues'].append(ue)
            else:
                ues = list()
                ues.append(ue)
                ue_filed = {'ues': ues}
                json_to_tx.update(ue_filed)
        else:  # ue already in the list information on RSRP has to be added
            for idx in range(0, len(json_to_tx['ues'])):
                if json_to_tx['ues'][idx]['rnti'] == ue_id:
                    json_to_tx['ues'][idx]['rsrp'] = payload_rx['ueMeasurement']['rsrp']

    else:  # this is not a serving cell
        ue_id = payload_rx['ueMeasurement']['ueRicId'].split('_')[1]

        if payload_rx['ueMeasurement']['cellId'] == 152:
            pci = 0
        else:
            pci = 1
        info_neighbor = {
            "pci": pci,
            "rsrp": payload_rx['ueMeasurement']['rsrp'],
            "rsrq": payload_rx['ueMeasurement']['rsrq']
        }
        neighborCells = list()
        neighborCells.append(info_neighbor)
        neighbor_field = {'neighborCells': neighborCells}
        if ue_id not in ue_list:
            ue_list.append(int(ue_id))
            json_to_tx['numUeDescriptors'] = json_to_tx['numUeDescriptors'] + 1
            ue = ue_info_2_tx
            ue['rnti'] = int(ue_id)
            ue['m-timsi'] = ue_id
            ue['mmec'] = int(ue_id)
            ue['numNeighborDescriptors'] = 1
            ue.update(neighbor_field)
            if 'ues' in json_to_tx:
                json_to_tx['ues'].append(ue)
            else:
                ues = list()
                ues.append(ue)
                ue_filed = {'ues': ues}
                json_to_tx.update(ue_filed)
        else:  # ue already in the list information on RSRP has to be added
            for idx in range(0, len(json_to_tx['ues'])):
                if json_to_tx['ues'][idx]['rnti'] == ue_id:
                    json_to_tx['ues'][idx]['numNeighborDescriptors'] = \
                        json_to_tx['ues'][idx]['numNeighborDescriptors'] + 1
                    if 'neighborCells' in json_to_tx['ues'][idx]:
                        json_to_tx['ues'][idx]['neighborCells'].append(info_neighbor)
                    else:
                        json_to_tx['ues'][idx].update(neighbor_field)
    return json_to_tx, ue_list


def parse_kafka_topics_from_settings(tmp_kafka_topics):
    kafka_topics = set()

    # Remove whitespace from string and split by commas
    parsed_kafka_topics = tmp_kafka_topics.replace(" ", "").split(',')

    for topic in parsed_kafka_topics:
        kafka_topics.add(topic)

    return kafka_topics


def run(settings, in_queue):

    logging.info("Starting Kafka listener...")
    fp_schema = open('schema.json', 'r')
    json_schema = json.load(fp_schema)
    # TODO create multi kafka topic support, use threads as listeners

    with settings.lock:
        kafka_url = settings.configuration['config']['KAFKA_URL']
        kafka_port = settings.configuration['config']['KAFKA_PORT']

    try:
        consumer = KafkaConsumer(
            bootstrap_servers=[kafka_url + ':' + kafka_port]
        )
        logging.info("Succesfully connected to Kafka server [{url}:{port}]".format(
            url=kafka_url,
            port=kafka_port
        ))
    except:
        logging.error("Failed to connect to Kafka Topic!")
        return

    tx_info = InstructiveInterface('node-info')
    # {
    # 'timestamp': 1590609372749960768, 'type': 'UE_MEASUREMENT',
    # 'ueMeasurement': {
    # 'cellId': 'Dageraadplaats', 'rsrp': 94, 'rsrq': 27, 'ueCellId': 'Dageraadplaats', 'ueRicId': 'UE_22520'
    # }
    # }

    default_json_152 = {
        "cpuLoad": 1.0,
        "eTime": 1963800,
        "numRruDescriptors": 1,
        "numUeDescriptors": 0,
        "sTime": 1963500,
        "rru": [
            {
                "dsThroughput": 1111,
                "ipAddress_p1": "x.y.z.k",
                "pci": 0,
                "rtt_latency": 1111,
                "usThroughput": 1111
            }
        ],
        "ues": []
        # "ues": [
        #    {
        #        "pci": 10,
        #        "rnti": 10,
        #        "tmsi_flag": 10,
        #        "mmec": 10,
        #        "m-timsi": "timsi",
        #        "dlThroughput": 10,
        #        "ulThroughput": 10,
        #        "rsrp": 10,
        #        "wbCqi": 10,
        #        "wbRi": 10,
        #        "puschSnr": 10,
        #        "pucchSnr": 10,
        #        "dlMcs": 10,
        #        "ulMcs": 10,
        #        "numDlRbs": 10,
        #        "numUlRbs": 10,
        #        "maxDlRank": 2,
        #        "maxDlMcs": 28,
        #        "maxUlMcs": 28,
        #        "maxNumDlRbs": 30,
        #        "maxNumUlRbs": 20,
        #        "rlcBufferDl": 10,
        #        "rlcBufferUl": 10,
        #        "numNeighborDescriptors": 10,
        # "neighborCells": [
        #    {
        #        "pci": 10,
        #        "rsrp": 10,
        #        "rsrq": 10
        #    },
        #    {
        #        "pci": 10,
        #        "rsrp": 10,
        #        "rsrq": 10
        #    },
        #    {
        #        "pci": 10,
        #        "rsrp": 10,
        #        "rsrq": 10
        #    }
        # ]
        #    }
        # ]
    }
    default_json_153 = {
        "cpuLoad": 1.0,
        "eTime": 1963800,
        "numRruDescriptors": 1,
        "numUeDescriptors": 0,
        "sTime": 1963500,
        "rru": [
            {
                "dsThroughput": 1111,
                "ipAddress_p1": "x.y.z.k",
                "pci": 1,
                "rtt_latency": 1111,
                "usThroughput": 1111
            }
        ],
        "ues": []
    }

    msg_start_152 = False
    msg_start_153 = False
    cell_152_on = False
    cell_153_on = False

    ue_list = list()

    accum_counter = 15

    counter = 0
    while True:
        with settings.lock:
            tmp_kafka_topics = settings.configuration['config']['KAFKA_LISTEN_TOPIC']

        kafka_topics = parse_kafka_topics_from_settings(tmp_kafka_topics)

        if consumer.subscription():
            if not kafka_topics.issubset(consumer.subscription()):
                consumer.subscribe(kafka_topics)
                logging.info('Subscribed to new topics: [{topics}]'.format(topics=kafka_topics))
        else:
            consumer.subscribe(kafka_topics)
            logging.info('Initial subscribe to topics: [{topics}]'.format(topics=kafka_topics))

        raw_msgs = consumer.poll(timeout_ms=1000)

        for tp, msgs in raw_msgs.items():

            for msg in msgs:
                payload = json.loads(msg.value)
                in_queue.put(payload)
                if 'type' in payload:
                    # logging.debug("Received on KAFKA:\n{msg}".format(msg=payload))
                    if payload['type'] == 'UE_MEASUREMENT':
                        # nats_queue.put(payload)
                        print("At [{time}] received msg type [{type}] that ue [{ue}] sees serving "
                              "cell [{s_cell}] and neighbour cell [{n_cell}]".format(time=datetime.datetime.fromtimestamp(payload['timestamp'] // 1000000000),
                              type=payload['type'],
                              n_cell=payload['ueMeasurement']['cellId'],
                              ue=payload['ueMeasurement']['ueRicId'],
                              s_cell=payload['ueMeasurement']['ueCellId'])
                              )
                        # ------------------------------------------------------------------------
                        # create json to TX for Cell 152
                        if payload['ueMeasurement']['cellId'] == 'Cell152':
                            if msg_start_152 is False:
                                default_json_152['sTime'] = payload['timestamp'] // 1000000000
                                msg_start_152 = True
                                default_json_152, ue_list = add_measurement_to_json(default_json_152, payload, ue_list)

                        if payload['ueMeasurement']['cellId'] == 'Cell153':
                            if msg_start_153 is False:
                                default_json_153['sTime'] = payload['timestamp'] // 1000000000
                                msg_start_153 = True
                                default_json_153, ue_list = add_measurement_to_json(default_json_153, payload, ue_list)

                    if payload['type'] == 'THROUGHPUT_REPORT':
                        print("At [{time}] received msg type [{type}] that ue [{ue}] sees serving cell [{cell}] "
                              "DL THR [{dlThroughput}], UL THR [{ulThroughput}]".format(
                              time=datetime.datetime.fromtimestamp(payload['timestamp'] // 1000000000),
                              type=payload['type'],
                              cell=payload['throughputReport']['cellId'],
                              ue=payload['throughputReport']['ueRicId'],
                              dlThroughput=payload['throughputReport']['dlThroughput'],
                              ulThroughput=payload['throughputReport']['ulThroughput'])
                              )

                    if payload['type'] == 'BLER_REPORT':
                        print("At [{time}] received msg type [{type}] that ue [{ue}] sees serving cell [{cell}] "
                              "DL BLER [{dlBler}], UL BLER [{ulBler}]".format(
                              time=datetime.datetime.fromtimestamp(payload['timestamp'] // 1000000000),
                              type=payload['type'],
                              cell=payload['blerReport']['cellId'],
                              ue=payload['blerReport']['ueRicId'],
                              dlBler=payload['blerReport']['dlBler'],
                              ulBler=payload['blerReport']['ulBler'])
                              )
                    if payload['type'] == 'CQI_REPORT':
                        print("-----------------")
                        print("Received CQI info")
                        print("-----------------")
                if 'beaconInfo' in payload:
                    print("Received Beacon {}".format(payload['beaconInfo']['componentId']))
                    if payload['beaconInfo']['componentId'] == "Cell152":
                        cell_152_on = True
                    if payload['beaconInfo']['componentId'] == "Cell153":
                        cell_153_on = True
        counter = counter + 1
        if counter == accum_counter:
            print('-----------------------------------')
            print('-----------------------------------')
            print('--    TX DATA TO Near RT RIC     --')
            print('-----------------------------------')
            print('-----------------------------------')

            if cell_152_on is True:
                try:
                    validate(default_json_152, json_schema)
                    tx_info.get_instance().tx_to_external_platform(default_json_152)
                except SchemaError as ex:
                    print("Schema for cell 152 is Not valid:\n{}".format(ex))
            if cell_153_on is True:
                try:
                    validate(default_json_153, json_schema)
                    tx_info.get_instance().tx_to_external_platform(default_json_153)
                except SchemaError as ex:
                    print("Schema for cell 153 is Not valid:\n{}".format(ex))

            # reset all variable
            counter = 0
            default_json_152 = {
                "cpuLoad": 1.0,
                "eTime": 1963800,
                "numRruDescriptors": 1,
                "numUeDescriptors": 0,
                "sTime": 1963500,
                "rru": [
                    {
                        "dsThroughput": 1111,
                        "ipAddress_p1": "x.y.z.k",
                        "pci": 0,
                        "rtt_latency": 1111,
                        "usThroughput": 1111
                    }
                ],
                "ues": []
            }
            default_json_153 = {
                "cpuLoad": 1.0,
                "eTime": 1963800,
                "numRruDescriptors": 1,
                "numUeDescriptors": 0,
                "sTime": 1963500,
                "rru": [
                    {
                        "dsThroughput": 1111,
                        "ipAddress_p1": "x.y.z.k",
                        "pci": 1,
                        "rtt_latency": 1111,
                        "usThroughput": 1111
                    }
                ],
                "ues": []
            }

            msg_start_152 = False
            msg_start_153 = False
            cell_152_on = False
            cell_153_on = False

            ue_list = list()

