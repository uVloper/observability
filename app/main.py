from flask import Flask, jsonify
import logging
import time
import random
import threading
import requests

from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

# NOVO: Imports para logs
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry._logs import set_logger_provider

# Criar um recurso compartilhado
resource = Resource.create({SERVICE_NAME: "python-app"})

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- TRACES ----
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
span_processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces")
)
trace.get_tracer_provider().add_span_processor(span_processor)

# ---- MÉTRICAS ----
reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://otel-collector:4318/v1/metrics")
)
provider = MeterProvider(resource=resource, metric_readers=[reader])

# ---- LOGS ----
log_provider = LoggerProvider(resource=resource)
log_exporter = OTLPLogExporter(endpoint="http://otel-collector:4318/v1/logs")
log_processor = BatchLogRecordProcessor(log_exporter)
log_provider.add_log_record_processor(log_processor)
set_logger_provider(log_provider)

# Conectar logs do Python com OpenTelemetry
otel_handler = LoggingHandler(level=logging.INFO)
logger.addHandler(otel_handler)

# ✅ Adicionar atributo service_name aos logs
def add_service_name_to_log_record_factory(service_name):
    original_factory = logging.getLogRecordFactory()
    def record_factory(*args, **kwargs):
        record = original_factory(*args, **kwargs)
        if not hasattr(record, "attributes"):
            record.attributes = {}
        record.attributes["service_name"] = service_name
        return record
    logging.setLogRecordFactory(record_factory)

add_service_name_to_log_record_factory("python-app")

# ---- Instrumentação automática ----
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
LoggingInstrumentor().instrument(set_logging_format=True)
RequestsInstrumentor().instrument()

# ---- Endpoints ----

@app.route("/")
def index():
    logger.info("Acessou o endpoint raiz")
    with tracer.start_as_current_span("process_request") as span:
        span.set_attribute("http.status_code", 200)
        span.set_attribute("name", "index")
        span.set_attribute("service.name", "python-app")
        time.sleep(random.uniform(0.1, 0.5))
    return "Hello Observabilidade!"

@app.route("/erro")
def erro():
    logger.warning("Simulando erro")
    with tracer.start_as_current_span("error_simulation") as span:
        span.set_attribute("http.status_code", 500)
        span.set_attribute("name", "erro")
        span.set_attribute("service.name", "python-app")
        span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, "Erro simulado"))
        raise Exception("Erro simulado!")

@app.route("/lento")
def lento():
    duration = random.uniform(1, 3)
    logger.info(f"Simulando latência de {duration:.2f}s")
    with tracer.start_as_current_span("slow_request") as span:
        span.set_attribute("http.status_code", 200)
        span.set_attribute("name", "lento")
        span.set_attribute("service.name", "python-app")
        time.sleep(duration)
    return jsonify({"message": "Resposta lenta", "delay": duration})

# ---- Geração de tráfego automático ----
def generate_internal_traffic():
    endpoints = ["http://localhost:8000/", "http://localhost:8000/lento", "http://localhost:8000/erro"]
    while True:
        try:
            url = random.choice(endpoints)
            requests.get(url)
        except Exception as e:
            logger.warning(f"Falha ao gerar tráfego: {e}")
        time.sleep(1)  # Aumente para menos se quiser mais tráfego

# ---- Início da aplicação ----
if __name__ == "__main__":
    threading.Thread(target=generate_internal_traffic, daemon=True).start()
    app.run(host="0.0.0.0", port=8000)
