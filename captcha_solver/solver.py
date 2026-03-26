import os
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
from tqdm import tqdm

device = "mps" if torch.backends.mps.is_available() else "cpu"
model_path = "./captcha_solver/fine_tuned_model"

processor = TrOCRProcessor.from_pretrained(model_path)
model = VisionEncoderDecoderModel.from_pretrained(model_path).to(device)


def solve_captcha(image_path):
    image = Image.open(image_path).convert("RGB")
    pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)

    generated_ids = model.generate(
        pixel_values,
        num_beams=5,
        max_new_tokens=10,
        early_stopping=True
    )
    result = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

    return "".join(result.split()).zfill(6)


if __name__ == '__main__':
    test_dir = "assets/test_captchas"
    files = [f for f in os.listdir(test_dir) if f.lower().endswith(('.png', '.jpg'))]

    correct = 0
    for filename in tqdm(files):
        expected = "".join(filter(str.isdigit, filename.split('.')[0]))
        predicted = solve_captcha(os.path.join(test_dir, filename))

        if predicted == expected:
            correct += 1
        else:
            print(f"Ошибка: Файл {filename} -> Предсказано: {predicted}")

    acc = (correct / len(files)) * 100
    print(f"\nИтоговая точность: {acc:.2f}% ({correct}/{len(files)})")
