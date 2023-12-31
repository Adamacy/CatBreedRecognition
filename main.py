import torch
import torchvision
import os
from torch.utils.data import DataLoader
from sklearn.metrics import f1_score

cats = ['Abyssinian', 'Bengal', 'Birman', 'Bombay', 'British Shorthair', 'Egyptian Mau', 'Maine Coon', 'Persian', 'Ragdoll', 'Russian Blue', 'Siamese', 'Sphynx']

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using {device}")

transform_rotation = torchvision.transforms.RandomApply([
    torchvision.transforms.RandomRotation(20)
], p = 0.2)
transform_train = torchvision.transforms.Compose([
    torchvision.transforms.Resize(256),
    torchvision.transforms.CenterCrop(224),
    torchvision.transforms.RandomPerspective(distortion_scale = 0.1, p = 0.2),
    transform_rotation,
    torchvision.transforms.ToTensor(),
    torchvision.transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
])

transform_valid = torchvision.transforms.Compose([
    torchvision.transforms.Resize(256),
    torchvision.transforms.CenterCrop(224),
    torchvision.transforms.ToTensor(),
    torchvision.transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
])

TRAIN_DATA_DIR = 'data/train'
VALID_DATA_DIR = 'data/valid'
TEST_DATA_DIR = 'data/test'

BATCH_SIZE = 32

train_data = torchvision.datasets.ImageFolder(TRAIN_DATA_DIR, transform = transform_train, is_valid_file = lambda x: x.endswith('.jpg'))
valid_data = torchvision.datasets.ImageFolder(VALID_DATA_DIR, transform = transform_valid, is_valid_file = lambda x: x.endswith('.jpg'))
test_data = torchvision.datasets.ImageFolder(TEST_DATA_DIR, transform = transform_valid, is_valid_file = lambda x: x.endswith('.jpg'))

train_data_loader = DataLoader(
    train_data,
    batch_size = BATCH_SIZE,
    shuffle = True,
    num_workers = 0
)
valid_data_loader = DataLoader(
    valid_data,
    batch_size = BATCH_SIZE,
    shuffle = False,
    num_workers = 0
)
test_data_loader = DataLoader(
    test_data,
    batch_size = BATCH_SIZE,
    shuffle = False,
    num_workers = 0
)

model = torchvision.models.resnet50(pretrained=True).to(device)

for parameter in model.parameters():
    parameter.requires_grad = False


class ModelHead(torch.nn.Module):
    def __init__(self, input_dim, hidden_dim, n_classes):
        super(ModelHead, self).__init__()
        self.fc1 = torch.nn.Linear(input_dim, hidden_dim)
        self.relu1 = torch.nn.ReLU()
        self.fc2 = torch.nn.Linear(hidden_dim, hidden_dim // 2)
        self.relu2 = torch.nn.ReLU()
        self.fc3 = torch.nn.Linear(hidden_dim // 2, n_classes)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.fc2(x)
        x = self.relu2(x)
        x = self.fc3(x)
        return x
    
model.fc = ModelHead(2048, 1024, 12) # type: ignore
model.fc.to(device)

MODEL_SAVE_PATH = 'checkpoints'
LEARNING_RATE = 1e-3
N_EPOCHS = 2

criterion = torch.nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr = LEARNING_RATE)

def train(model, n_epochs, criterion, optimizer, train_data_loader, valid_data_loader, device, model_save_path, logging_interval: int = 50):
    best_valid_f1_score = 0.0

    os.makedirs(model_save_path, exist_ok=True)

    for epoch in range(n_epochs):
        model.train()

        for batch_idx, (batch_data, batch_labels) in enumerate(train_data_loader):
            inputs = batch_data.to(device)
            y_true = batch_labels.to(device)

            optimizer.zero_grad()

            y_pred = model(inputs)
            loss = criterion(y_pred, y_true)
            loss.backward()
            optimizer.step()

            if (batch_idx + 1) % logging_interval == 0:
                print(f"Epoch {epoch + 1}\t| Batch: {batch_idx + 1}\t| Loss: {loss}")


        model.eval()
        y_true = []
        y_pred = []
        for valid_data, valid_labels in valid_data_loader:
            valid_data = valid_data.to(device)
            valid_labels = valid_labels.to(device)
            with torch.no_grad():
                valid_preds = model(valid_data)
            valid_pred_labels = torch.argmax(valid_preds, dim=1)
            y_true.extend(valid_labels.detach().cpu().numpy())
            y_pred.extend(valid_pred_labels.detach().cpu().numpy())
        valid_f1_score = f1_score(y_true, y_pred, average='macro')

        if valid_f1_score > best_valid_f1_score:
            best_valid_f1_score = valid_f1_score
            torch.save(model.state_dict(),
                       os.path.join(model_save_path, 'best_checkpoint.pth'))
        print(f'Epoch {epoch + 1} F1-score: {valid_f1_score}\t| Best F1-score: {best_valid_f1_score}')
        torch.save(model.state_dict(), os.path.join(model_save_path, f'epoch_{epoch + 1}_checkpoint.pth'))


#train(model, N_EPOCHS, criterion, optimizer, train_data_loader, valid_data_loader, device, MODEL_SAVE_PATH)

# Testing
model.load_state_dict(torch.load(os.path.join(MODEL_SAVE_PATH, 'best_checkpoint.pth')))
model.eval()

from PIL import Image

def check_image(image): # type: ignore
    
    img = Image.open(image)

    transform = torchvision.transforms.ToTensor()
    torch_tensor = transform(img)

    x = torch_tensor.unsqueeze(0)

    output = model(x)

    pred = torch.argmax(output, 1)
    return cats[int(pred)]
