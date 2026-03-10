"""
ADT A01 Kafka Consumer → FHIR R4
Consumes ADT messages from Kafka, maps them to FHIR resources,
and POSTs Patient + Encounter to the public HAPI FHIR server.
"""

import json
import sys
from confluent_kafka import Consumer, KafkaException, KafkaError

from fhir_mapper import build_fhir_patient, build_fhir_encounter
from fhir_client import FHIRClient

# ── Config ────────────────────────────────────────────────────────────────────
KAFKA_BROKER    = "localhost:9092"
TOPIC           = "adt-stream"
GROUP_ID        = "adt-fhir-consumer-group"
AUTO_OFFSET     = "earliest"   # replay from beginning if no committed offset


def create_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers":  KAFKA_BROKER,
            "group.id":           GROUP_ID,
            "auto.offset.reset":  AUTO_OFFSET,
            "enable.auto.commit": True,
        }
    )


def process_message(msg_value: str, fhir: FHIRClient) -> None:
    """Parse one ADT payload, create FHIR Patient then Encounter."""
    try:
        adt = json.loads(msg_value)
    except json.JSONDecodeError as e:
        print(f"[WARN] Could not parse message JSON: {e}")
        return

    print(f"\n{'─'*60}")
    print(f"[MSG]  event={adt.get('event_type')} | "
          f"msg_id={adt.get('message_id')} | "
          f"patient={adt['patient']['last_name']}, {adt['patient']['first_name']}")

    # 1. Build FHIR resources
    patient_resource  = build_fhir_patient(adt)
    # Placeholder ID — will be replaced after Patient is created
    encounter_resource = build_fhir_encounter(adt, "PENDING")

    # 2. POST Patient → get logical FHIR id
    patient_fhir_id = fhir.create_patient(patient_resource)
    if not patient_fhir_id:
        print("[SKIP] Patient creation failed; skipping Encounter.")
        return

    # 3. POST Encounter linked to the new Patient
    encounter_resource = build_fhir_encounter(adt, patient_fhir_id)
    fhir.create_encounter(encounter_resource, patient_fhir_id)


def main():
    print("=" * 60)
    print("  ADT A01 → FHIR Consumer")
    print(f"  Broker : {KAFKA_BROKER}")
    print(f"  Topic  : {TOPIC}")
    print(f"  Group  : {GROUP_ID}")
    print("=" * 60)

    consumer = create_consumer()
    fhir     = FHIRClient()

    consumer.subscribe([TOPIC])
    print(f"[READY] Subscribed to '{TOPIC}'. Waiting for messages…\n")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"[INFO] Reached end of partition {msg.partition()}")
                else:
                    raise KafkaException(msg.error())
                continue

            process_message(msg.value().decode("utf-8"), fhir)

    except KeyboardInterrupt:
        print("\n[STOP] Consumer interrupted.")
    finally:
        consumer.close()
        print("[DONE] Consumer closed.")


if __name__ == "__main__":
    main()
