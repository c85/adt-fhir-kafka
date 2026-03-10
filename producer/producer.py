"""
ADT A01 (Admit) Kafka Producer
Generates synthetic HL7 v2.x ADT^A01 messages and streams them to Kafka.
"""

import json
import random
import time
import uuid
from datetime import datetime, timezone
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic

# ── Config ────────────────────────────────────────────────────────────────────
KAFKA_BROKER = "localhost:9092"
TOPIC        = "adt-stream"
INTERVAL_SEC = 3          # seconds between messages (set to 0 for burst)
MESSAGE_COUNT = 0          # 0 = run forever

# ── Synthetic data pools ──────────────────────────────────────────────────────
FIRST_NAMES = ["James", "Maria", "David", "Sarah", "Kevin", "Aisha",
                "Chen", "Priya", "Lucas", "Fatima"]
LAST_NAMES  = ["Smith", "Patel", "Johnson", "Kim", "Garcia", "Nguyen",
                "Williams", "Brown", "Davis", "Martinez"]
GENDERS     = ["M", "F", "U"]
FACILITIES  = ["General Hospital", "City Medical Center", "Riverside Clinic"]
WARDS       = ["ICU", "CARDIAC", "NEUROLOGY", "ORTHOPEDICS", "ONCOLOGY"]
PHYSICIANS  = [
    ("1234567890", "Dr. Emily Chen"),
    ("0987654321", "Dr. Marcus Webb"),
    ("1122334455", "Dr. Amara Osei"),
]


def random_dob() -> str:
    """Return a random DOB (age 18–90) in HL7 format YYYYMMDD."""
    year = random.randint(1934, 2006)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year}{month:02d}{day:02d}"


def hl7_timestamp(dt: datetime = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y%m%d%H%M%S")


def build_adt_a01(patient_id: str) -> dict:
    """Build a structured representation of an HL7 ADT^A01 message."""
    first  = random.choice(FIRST_NAMES)
    last   = random.choice(LAST_NAMES)
    gender = random.choice(GENDERS)
    dob    = random_dob()
    npi, physician_name = random.choice(PHYSICIANS)
    facility = random.choice(FACILITIES)
    ward     = random.choice(WARDS)
    admit_dt = hl7_timestamp()
    msg_ctrl = str(uuid.uuid4()).replace("-", "")[:20].upper()

    # Raw HL7 v2.x segment string (pipe-delimited)
    hl7_raw = (
        f"MSH|^~\\&|ADT_PRODUCER|{facility}|FHIR_CONSUMER|HAPI|{admit_dt}||ADT^A01^ADT_A01|{msg_ctrl}|P|2.5.1\r"
        f"EVN|A01|{admit_dt}|||{npi}^{physician_name}\r"
        f"PID|1||{patient_id}^^^{facility}^MR||{last}^{first}^^^||{dob}|{gender}|||123 Main St^^Springfield^IL^62701^USA\r"
        f"PV1|1|I|{ward}^101^A|||{npi}^{physician_name}|||SUR||||ADM|{admit_dt}\r"
    )

    return {
        "message_id":     msg_ctrl,
        "event_type":     "ADT^A01",
        "timestamp":      admit_dt,
        "patient": {
            "id":         patient_id,
            "first_name": first,
            "last_name":  last,
            "gender":     gender,
            "dob":        dob,
        },
        "encounter": {
            "facility":   facility,
            "ward":       ward,
            "admit_dt":   admit_dt,
            "physician":  {"npi": npi, "name": physician_name},
        },
        "hl7_raw": hl7_raw,
    }


def ensure_topic(broker: str, topic: str) -> None:
    admin = AdminClient({"bootstrap.servers": broker})
    existing = admin.list_topics(timeout=10).topics
    if topic not in existing:
        fs = admin.create_topics([NewTopic(topic, num_partitions=3, replication_factor=1)])
        for t, f in fs.items():
            try:
                f.result()
                print(f"[ADMIN] Created topic '{t}'")
            except Exception as e:
                print(f"[ADMIN] Topic '{t}' may already exist: {e}")


def delivery_report(err, msg):
    if err:
        print(f"[ERROR] Delivery failed: {err}")
    else:
        print(f"[SENT]  partition={msg.partition()} offset={msg.offset()} | "
              f"patient={json.loads(msg.value())['patient']['last_name']}")


def main():
    print("=" * 60)
    print("  ADT A01 Stream Producer")
    print(f"  Broker : {KAFKA_BROKER}")
    print(f"  Topic  : {TOPIC}")
    print("=" * 60)

    ensure_topic(KAFKA_BROKER, TOPIC)

    producer = Producer({"bootstrap.servers": KAFKA_BROKER})

    count = 0
    try:
        while True:
            patient_id = f"PT-{random.randint(10000, 99999)}"
            message    = build_adt_a01(patient_id)

            producer.produce(
                topic=TOPIC,
                key=patient_id,
                value=json.dumps(message),
                callback=delivery_report,
            )
            producer.poll(0)

            count += 1
            if MESSAGE_COUNT and count >= MESSAGE_COUNT:
                break

            time.sleep(INTERVAL_SEC)

    except KeyboardInterrupt:
        print("\n[STOP] Producer interrupted.")
    finally:
        producer.flush()
        print(f"[DONE] Produced {count} message(s).")


if __name__ == "__main__":
    main()
