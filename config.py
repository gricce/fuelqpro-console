import os
from google.cloud import storage

# Debug mode
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

# API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Google Cloud Storage setup
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "fuelqpro-pdfs")
storage_client = storage.Client()

# Initialize storage bucket
try:
    storage_bucket = storage_client.get_bucket(GCS_BUCKET_NAME)
except Exception:
    try:
        storage_bucket = storage_client.create_bucket(GCS_BUCKET_NAME)
    except Exception as e:
        print(f"Could not create or access bucket: {e}")
        storage_bucket = None

# Questionnaire steps
STEPS = [
    ("name", "Olá, Bem vindo ao FuelQ Pro! Vamos a uma jornada bem divertida e interessante para você ter mais performance, mas antes me diga seu nome?"),
    ("age", "Ok, e qual a sua idade?"),
    ("experience", "Qual o seu nível de experiência em esportes? (Iniciante, Intermediário, Avançado)"),
    ("sports", "Quais esportes você pratica? (Ciclismo, Corrida, Natação, etc.)"),
    ("events", "Quais eventos você tem em mente? (Corrida 5k, Corrida 10k, Ciclismo, MTB, Triathlon etc.)"),
    ("gender", "Qual o seu Sexo (Masculino/Feminino)?"),
    ("weight", "Me diga qual seu peso em Kg?"),
    ("height", "E sua altura em Centímetros?"),
    ("diet", "Que tipo de dieta você segue? (ex: Como de tudo, Vegano, Vegetariano, etc.)"),
    ("allergies", "Algum alimento te causa alergia?"),
    ("carb_adapted", "Você está adaptado a altas quantidades de carbo nos dias de treino longo ou competição? (Sim/Não)"),
    ("training_hours", "Quantas horas em média você treina na semana?"),
    ("cramps", "Você tem cãibras musculares durante seus treinos? (Sim/Não)"),
    ("plan_type", "Como você gostaria de receber seu plano alimentar? (Diário ou Semanal)")
]

# Field labels
LABELS = {
    "name": "Nome",
    "age": "Idade",
    "experience": "Nível de experiência",
    "sports": "Esportes praticados",
    "events": "Eventos de interesse",
    "gender": "Sexo",
    "weight": "Peso (kg)",
    "height": "Altura (cm)",
    "diet": "Tipo de dieta",
    "allergies": "Alergias alimentares",
    "carb_adapted": "Adaptado a alto consumo de carboidrato?",
    "training_hours": "Horas de treino por semana",
    "cramps": "Cãibras frequentes?",
    "plan_type": "Tipo de plano desejado"
}