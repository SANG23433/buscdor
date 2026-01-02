import time
import asyncio
import numpy as np
import requests
from io import BytesIO
from PIL import Image
from google import genai

class VisionService:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.5-flash-preview-09-2025" # Actualizado a la versión sugerida

    async def _call_with_retry(self, func, *args, **kwargs):
        """Implementa backoff exponencial: 1s, 2s, 4s, 8s, 16s"""
        delays = [1, 2, 4, 8, 16]
        for i, delay in enumerate(delays):
            try:
                # Ejecutar la llamada síncrona de la SDK en un thread para no bloquear el loop
                return await asyncio.to_thread(func, *args, **kwargs)
            except Exception as e:
                if i == len(delays) - 1:
                    raise e
                await asyncio.sleep(delay)
        return None

    def calculate_cosine_similarity(self, vec_a, vec_b):
        if vec_a is None or vec_b is None: return 0
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        return float(dot_product / (norm_a * norm_b)) if (norm_a > 0 and norm_b > 0) else 0

    async def get_image_description(self, image_url):
        try:
            res = requests.get(image_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            img = Image.open(BytesIO(res.content))
            prompt = "Describe esta imagen detalladamente para comparación de logos inmobiliarios. Un párrafo denso."
            
            response = await self._call_with_retry(
                self.client.models.generate_content,
                model=self.model_id, 
                contents=[prompt, img]
            )
            return response.text if response else None
        except Exception:
            return None

    async def get_text_embedding(self, text):
        if not text: return None
        try:
            res = await self._call_with_retry(
                self.client.models.embed_content,
                model="text-embedding-004", 
                contents=text
            )
            return res.embeddings[0].values if res else None
        except Exception:
            return None