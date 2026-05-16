from openai import AzureOpenAI, OpenAI
from ..config import settings


HF_MODELS = {
    "deepseek": settings.HF_MODEL,
    "llama":    settings.LLAMA_MODEL,
}


def get_llm_client(provider: str = "deepseek"):
    if provider == "gemma":
        client = AzureOpenAI(
            api_key=settings.GEMMA_API_KEY,
            azure_endpoint=settings.GEMMA_ENDPOINT,
            api_version=settings.GEMMA_API_VERSION,
        )
        return client, settings.GEMMA_DEPLOYMENT
    else:
        client = OpenAI(
            base_url=settings.HF_BASE_URL,
            api_key=settings.HF_TOKEN,
        )
        model = HF_MODELS.get(provider, settings.HF_MODEL)
        return client, model


def chat_completion(messages: list, provider: str = "deepseek", **kwargs) -> str:
    client, model = get_llm_client(provider)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        **kwargs,
    )
    return response.choices[0].message.content
