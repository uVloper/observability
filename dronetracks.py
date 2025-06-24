from flask import Flask, jsonify
import threading
import time
from prometheus_flask_exporter import PrometheusMetrics

from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# 1. Defina o recurso com o nome correto do serviço
resource = Resource(attributes={
    SERVICE_NAME: "dronetracks"
})

# 2. Configure o tracer provider com o recurso
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# 3. Crie o app Flask
app = Flask(__name__)

# 4. Instrumente o Flask depois de definir o provider
FlaskInstrumentor().instrument_app(app)

# 5. Ative o Prometheus
metrics = PrometheusMetrics(app)

# Simulação de coordenadas
drone_location = {
    "latitude": 0.0,
    "longitude": 0.0
}

def update_location():
    while True:
        drone_location["latitude"] += 0.001
        drone_location["longitude"] += 0.001
        time.sleep(1)

@app.route('/location')
def get_location():
    return jsonify(drone_location)

if __name__ == '__main__':
    threading.Thread(target=update_location, daemon=True).start()
    app.run(host="0.0.0.0", port=5100)
