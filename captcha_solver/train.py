import pandas as pd
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, TrainingArguments, Trainer
from torch.utils.data import Dataset
from PIL import Image
from torchvision import transforms
import os



dataset_path = "../assets/dataset_captchas" 


data = []
for filename in os.listdir(dataset_path):
    if filename.endswith((".jpg", ".png", ".jpeg")):
        # Извлекаем только цифры из названия (например, '331945.jpg' -> '331945')
        clean_text = "".join(filter(str.isdigit, filename.split('.')[0]))
        if clean_text:
            data.append({"file_name": filename, "text": clean_text})

df = pd.DataFrame(data)
df.to_csv("metadata.csv", index=False)
print(f"Готово! Создан файл metadata.csv с {len(df)} записями.")



# Проверка устройства
if torch.backends.mps.is_available():
    device = torch.device("mps")
    print("🚀 Используем Apple Silicon GPU (MPS)")
else:
    device = torch.device("cpu")
    print("⚠️ MPS не доступен, используем CPU")

class CaptchaDataset(Dataset):
    def __init__(self, root_dir, df, processor, max_target_length=10):
        self.root_dir = root_dir
        self.df = df
        self.processor = processor
        self.max_target_length = max_target_length
        self.transform = transforms.Compose([
            transforms.ColorJitter(brightness=0.3, contrast=0.3),
            transforms.RandomRotation(degrees=8), # Немного увеличили угол
        ])

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        file_name = self.df.iloc[idx]['file_name']
        text = str(self.df.iloc[idx]['text'])
        img_path = os.path.join(self.root_dir, file_name)
        
        image = Image.open(img_path).convert("RGB")
        image = self.transform(image)
        
        pixel_values = self.processor(image, return_tensors="pt").pixel_values
        labels = self.processor.tokenizer(text, padding="max_length", max_length=self.max_target_length).input_ids
        labels = [label if label != self.processor.tokenizer.pad_token_id else -100 for label in labels]

        return {"pixel_values": pixel_values.squeeze(), "labels": torch.tensor(labels)}

# Загрузка
model_id = "microsoft/trocr-small-printed"
processor = TrOCRProcessor.from_pretrained(model_id)
model = VisionEncoderDecoderModel.from_pretrained(model_id).to(device)

# Конфиг
model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
model.config.pad_token_id = processor.tokenizer.pad_token_id
model.config.vocab_size = model.config.decoder.vocab_size

# Данные
df = pd.read_csv("metadata.csv")
train_dataset = CaptchaDataset(root_dir=dataset_path, df=df, processor=processor)

training_args = TrainingArguments(
    output_dir="./checkpoint",
    per_device_train_batch_size=4,
    num_train_epochs=125, 
    learning_rate=4e-5,
    save_strategy="no",
    logging_steps=10,
    weight_decay=0.01,
    remove_unused_columns=False,
)


trainer = Trainer(
    model=model, 
    args=training_args, 
    train_dataset=train_dataset
)

print("Начинаю обучение...")
trainer.train()

# Сохранение
model.save_pretrained("./fine_tuned_model")
processor.save_pretrained("./fine_tuned_model")
print("🎯 Модель успешно сохранена!")


# 100
# 📊 Итоговая точность: 27.78% (5/18)
# 125
# Итоговая точность: 55.56% (10/18)
# 150
# 📊 Итоговая точность: 55.56% (10/18)
# 200
# 📊 Итоговая точность: 33.33% (6/18)
# 500
# 📊 Итоговая точность: 22.222% (4/18)
