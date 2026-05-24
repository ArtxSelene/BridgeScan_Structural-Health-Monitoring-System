from torch.utils.data import Dataset, DataLoader
import glob
import os
import numpy as np
import cv2
import torch

class SegDataset(Dataset):
    def __init__(self, root_dir, imageFolder, maskFolder, transform=None):
        self.root_dir = root_dir
        self.transform = transform
        
        # MAPPING
        self.mapping = {
            (0, 0, 0): 0,     # Black -> Good
            (128, 0, 0): 1,   # Dark Red -> Fair
            (0, 128, 0): 2,   # Green -> Poor
            (128, 128, 0): 3  # Yellow -> Severe
        }
        
        # FIX: Paggamit ng tamang path at pag-handle ng extensions
        self.image_names = sorted(glob.glob(os.path.join(root_dir, imageFolder, '*.*')))
        self.mask_names = sorted(glob.glob(os.path.join(root_dir, maskFolder, '*.*')))
        
        if len(self.image_names) == 0:
            print(f"BABALA: Walang nahanap na images sa {os.path.join(root_dir, imageFolder)}")

    def __len__(self):
        return len(self.image_names)

    def __getitem__(self, idx):
        # Read Image (BGR to RGB)
        image = cv2.imread(self.image_names[idx])
        if image is None:
            raise ValueError(f"Image not found/corrupted: {self.image_names[idx]}")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Read Mask (BGR to RGB)
        mask_rgb = cv2.imread(self.mask_names[idx])
        if mask_rgb is None:
            raise ValueError(f"Mask not found/corrupted: {self.mask_names[idx]}")
        mask_rgb = cv2.cvtColor(mask_rgb, cv2.COLOR_BGR2RGB)

        # Mapping RGB to Class Indices
        h, w, _ = mask_rgb.shape
        mask = torch.zeros((h, w), dtype=torch.long)
        
        for color, class_idx in self.mapping.items():
            match = np.all(mask_rgb == np.array(color), axis=-1)
            mask[match] = class_idx

        # Normalization (0-1) at channel-first adjustment
        image = torch.from_numpy(image.transpose(2, 0, 1)).float() / 255.0
        
        return {'image': image, 'mask': mask}

def get_dataloader_sep_folder(data_dir, batch_size):
    # Setup paths para sa Train at Test
    train_ds = SegDataset(data_dir, 'Train/images_512', 'Train/mask_512')
    test_ds = SegDataset(data_dir, 'Test/images_512', 'Test/mask_512')
    
    dataloaders = {
        'Train': DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=2, pin_memory=True),
        'Test': DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=2, pin_memory=True)
    }
    return dataloaders