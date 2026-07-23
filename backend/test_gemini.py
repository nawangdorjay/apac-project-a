from dotenv import load_dotenv
load_dotenv()
from services.safe_gemini import safe_generate, get_status, GeminiFallbackError

print("Status:", get_status())

try:
    text = safe_generate("Say hello in one word.", json_mode=False, max_tokens=10)
    print("Gemini response:", text)
    print("\n✅ API key is working! Gemini is connected.")
except GeminiFallbackError as e:
    print(f"\n❌ Gemini error: {e}")
