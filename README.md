# ADT → FHIR Streaming PoC

> A proof-of-concept demonstrating real-time HL7 ADT event streaming via **Apache Kafka**, with automated translation to **FHIR R4** resources and live posting to the public **HAPI FHIR** server.

---

## 🏗️ Architecture

```
┌─────────────────────┐        ┌──────────────┐        ┌──────────────────────┐
│   ADT Producer      │        │    Kafka     │        │   FHIR Consumer      │
│                     │        │              │        │                      │
│  Synthetic HL7      │──────▶│  adt-stream  │──────▶│  HL7 → FHIR Mapper   │
│  ADT^A01 messages   │  pub  │  (topic)     │  sub  │  confluent-kafka      │
│  (confluent-kafka)  │        │              │        │        │             │
└─────────────────────┘        └──────────────┘        │        ▼             │
                                                       │  HAPI FHIR R4        │
                                                       │  POST /Patient       │
                                                       │  POST /Encounter     │
                                                       └──────────────────────┘
```

**Flow:**

1. **Producer** generates synthetic HL7 v2.5.1 `ADT^A01` (Admit) messages and publishes them to the `adt-stream` Kafka topic
2. **Consumer** polls the topic, parses each message, and maps it to FHIR R4 resources:
   - `Patient` — demographic data from the `PID` segment
   - `Encounter` — admission data from the `PV1` segment
3. Both resources are `POST`ed to the public **HAPI FHIR R4** server (`https://hapi.fhir.org/baseR4`)
4. **Dashboard** (`dashboard/index.html`) provides a live visual of the stream with message inspection

---

## 🛠️ Tech Stack

| Layer         | Technology                       |
|---------------|----------------------------------|
| Message broker| Apache Kafka (via Docker)        |
| Producer      | Python · `confluent-kafka`       |
| Consumer      | Python · `confluent-kafka`       |
| FHIR mapping  | Custom HL7 → FHIR R4 mapper      |
| FHIR server   | Public HAPI FHIR R4              |
| Dashboard     | Vanilla HTML/CSS/JS              |
| Infra         | Docker Compose                   |

---

## 📁 Project Structure

```
adt-fhir-kafka/
├── docker-compose.yml          # Kafka + Zookeeper + Kafka UI
├── requirements.txt            # Python dependencies
│
├── producer/
│   └── producer.py             # Synthetic ADT^A01 message producer
│
├── consumer/
│   ├── consumer.py             # Kafka consumer → FHIR pipeline
│   ├── fhir_mapper.py          # HL7 segment → FHIR R4 resource mapper
│   └── fhir_client.py          # HTTP client for HAPI FHIR server
│
└── dashboard/
    └── index.html              # Live stream visualization dashboard
```

---

## 🚀 Quick Start

### Prerequisites

- Docker + Docker Compose
- Python 3.9+

### 1. Start Kafka

```bash
docker-compose up -d
```

This starts:
- **Zookeeper** on port `2181`
- **Kafka broker** on port `9092`
- **Kafka UI** at [http://localhost:8080](http://localhost:8080)

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Consumer

```bash
cd consumer
python consumer.py
```

The consumer subscribes to `adt-stream` and will block, waiting for messages.

### 4. Start the Producer (new terminal)

```bash
cd producer
python producer.py
```

The producer begins emitting one `ADT^A01` message every 3 seconds.

### 5. Open the Dashboard

Open `dashboard/index.html` in any browser — no server required.

---

## 🔍 What You'll See

**Producer terminal:**
```
[SENT]  partition=0 offset=0 | patient=Garcia
[SENT]  partition=2 offset=1 | patient=Patel
```

**Consumer terminal:**
```
────────────────────────────────────────────────────────────
[MSG]  event=ADT^A01 | msg_id=A3F9C2... | patient=Garcia, Lucas
[FHIR] Patient created → id=9821043  name=Garcia, Lucas
[FHIR] Encounter created → id=9821044  patient=Patient/9821043
```

**HAPI FHIR** — verify resources at:
- `https://hapi.fhir.org/baseR4/Patient?identifier=PT-XXXXX`
- `https://hapi.fhir.org/baseR4/Encounter?subject=Patient/XXXXXX`

---

## 📐 FHIR R4 Mapping

### HL7 PID Segment → FHIR Patient

| HL7 Field        | FHIR Field                    |
|------------------|-------------------------------|
| `PID-3`          | `Patient.identifier` (MR)     |
| `PID-5`          | `Patient.name`                |
| `PID-7`          | `Patient.birthDate`           |
| `PID-8`          | `Patient.gender`              |

### HL7 PV1 Segment → FHIR Encounter

| HL7 Field        | FHIR Field                        |
|------------------|-----------------------------------|
| `PV1-2`          | `Encounter.class` (IMP)           |
| `PV1-3`          | `Encounter.location`              |
| `PV1-7`          | `Encounter.participant` (ATND)    |
| `PV1-44`         | `Encounter.period.start`          |

---

## ⚙️ Configuration

| Variable         | File             | Default                        | Description                  |
|------------------|------------------|--------------------------------|------------------------------|
| `KAFKA_BROKER`   | producer/consumer| `localhost:9092`               | Kafka bootstrap server       |
| `TOPIC`          | producer/consumer| `adt-stream`                   | Kafka topic name             |
| `INTERVAL_SEC`   | producer.py      | `3`                            | Seconds between messages     |
| `FHIR_BASE_URL`  | fhir_client.py   | `https://hapi.fhir.org/baseR4` | FHIR server base URL         |

---

## 🧪 Extending This PoC

- **Add A03/A08 events** — extend `producer.py` with additional event types and update the mapper
- **Schema Registry** — add Confluent Schema Registry for Avro-encoded messages
- **Error dead-letter queue** — route failed FHIR POSTs to a separate Kafka topic
- **Persistent FHIR server** — swap HAPI public for a local Docker HAPI instance
- **Monitoring** — add Prometheus metrics to the consumer

---

## 📄 License

MIT
