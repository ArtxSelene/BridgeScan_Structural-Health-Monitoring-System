from torch.utils.data import Dataset, DataLoader
import glob
import os
import numpy as np
import cv2
import torch
from torchvision import transforms

class SegDataset(Dataset):
    def __init__(self, root_dir, imageFolder, maskFolder, transform=None):
        self.root_dir = root_dir
        self.transform = transform
        
        # Pagbuo ng path gamit ang os.path.join para iwas error sa folder separators
        img_search_path = os.path.join(self.root_dir, imageFolder, '*')
        msk_search_path = os.path.join(self.root_dir, maskFolder, '*')
        
        self.image_names = sorted(glob.glob(img_search_path))
        self.mask_names = sorted(glob.glob(msk_search_path))
        
        print(f"DEBUG: Nag-initialize sa {root_dir}")
        print(f"DEBUG: Nakahanap ng {len(self.image_names)} images at {len(self.mask_names)} masks.")

    def __len__(self):
        return len(self.image_names)

    def __getitem__(self, idx):
        image = cv2.imread(self.image_names[idx])
        mask = cv2.imread(self.mask_names[idx], cv2.IMREAD_GRAYSCALE)
        
        # MAPPING: 0, 38, 76, 114 -> 0, 1, 2, 3
        new_mask = np.zeros_like(mask, dtype=np.int64)
        new_mask[mask == 0] = 0
        new_mask[mask == 38] = 1
        new_mask[mask == 76] = 2
        new_mask[mask == 114] = 3
        
        sample = {'image': image, 'mask': new_mask}
        if self.transform:
            sample = self.transform(sample)
        return sample

class ToTensor(object):
    def __call__(self, sample):
        image, mask = sample['image'], sample['mask']
        # Convert to tensor at gawing float (0-1)
        image = torch.from_numpy(image.transpose((2, 0, 1))).float() / 255.0
        mask = torch.from_numpy(mask).long()
        return {'image': image, 'mask': mask}

def get_dataloader_sep_folder(data_dir, imageFolder='images_512', maskFolder='mask_512', batch_size=4):
    data_transforms = transforms.Compose([ToTensor()])
    
    dataloaders = {}
    for x in ['Train', 'Test']:
        folder_path = os.path.join(data_dir, x)
        
        # I-initialize ang dataset
        dataset = SegDataset(root_dir=folder_path, 
                             transform=data_transforms, 
                             maskFolder=maskFolder, 
                             imageFolder=imageFolder)
        
        if len(dataset) == 0:
            print(f"CRITICAL ERROR: {x} folder ay walang laman!")
            # Dito natin ilalagay ang exit para hindi na mag-crash ang DataLoader
            raise ValueError(f"Walang samples sa {folder_path}")
            
        # Paggamit ng num_workers=0 para iwas error sa multiprocessing sa Colab
        dataloaders[x] = DataLoader(dataset, 
                                    batch_size=batch_size, 
                                    shuffle=True, 
                                    num_workers=0, 
                                    drop_last=True)
        print(f"DEBUG: {x} Dataloader created successfully.")
    
    return dataloaders