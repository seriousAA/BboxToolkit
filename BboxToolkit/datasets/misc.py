import itertools
import os.path as osp
import numpy as np

from tqdm import tqdm
from multiprocessing import Pool
from ..imagesize import imsize


def product(*inputs):
    return [''.join(e) for e in itertools.product(*inputs)]

dataset_classes = {
    'DOTA1_0': ('large-vehicle', 'swimming-pool', 'helicopter', 'bridge',
                'plane', 'ship', 'soccer-ball-field', 'basketball-court',
                'ground-track-field', 'small-vehicle', 'baseball-diamond',
                'tennis-court', 'roundabout', 'storage-tank', 'harbor'),
    'DOTA1_5': ('large-vehicle', 'swimming-pool', 'helicopter', 'bridge',
                'plane', 'ship', 'soccer-ball-field', 'basketball-court',
                'ground-track-field', 'small-vehicle', 'baseball-diamond',
                'tennis-court', 'roundabout', 'storage-tank', 'harbor',
                'container-crane'),
    'DOTA2_0': ('large-vehicle', 'swimming-pool', 'helicopter', 'bridge',
                'plane', 'ship', 'soccer-ball-field', 'basketball-court',
                'ground-track-field', 'small-vehicle', 'baseball-diamond',
                'tennis-court', 'roundabout', 'storage-tank', 'harbor',
                'container-crane', 'airport', 'helipad'),
    'DOTA_GSD_2025_03': ('large-vehicle', 'swimming-pool', 'helicopter', 'bridge',
                'plane', 'ship', 'soccer-ball-field', 'basketball-court',
                'ground-track-field', 'small-vehicle', 'baseball-diamond',
                'tennis-court', 'roundabout', 'storage-tank', 'harbor',
                'container-crane', 'helipad'),
    'DIOR': ('airplane', 'airport', 'baseballfield', 'basketballcourt', 'bridge',
             'chimney', 'expressway-service-area', 'expressway-toll-station',
             'dam', 'golffield', 'groundtrackfield', 'harbor', 'overpass', 'ship',
             'stadium', 'storagetank', 'tenniscourt', 'trainstation', 'vehicle',
             'windmill'),
    'HRSC': ('ship', ),
    'HRSC_cls': ('01', '02', '03', '04', '05', '06', '07', '08', '09', '10',
                 '11', '12', '13', '14', '15', '16', '17', '18', '19', '20',
                 '21', '22', '23', '24', '25', '26', '27', '28', '29', '30',
                 '31', '32', '33'),
    'MSRA_TD500': ('text', ),
    'HUST_TR400': ('text', ),
    'RCTW_17': ('text', ),
    'SynthText': ('text', ),
    'ICDAR2015': ('text', ),
    'VOC': ('person', 'bird', 'cat', 'cow', 'dog', 'horse', 'sheep', 'aeroplane',
            'bicycle', 'boat', 'bus', 'car', 'motorbike', 'train', 'bottle',
            'chair', 'diningtable', 'pottedplant', 'sofa', 'tvmonitor'),
}

dataset_aliases = {
    'DOTA1_0': product(['dota', 'DOTA'], ['', '1', '1.0', '1_0']),
    'DOTA1_5': product(['dota', 'DOTA'], ['1.5', '1_5']),
    'DOTA2_0': product(['dota', 'DOTA'], ['2', '2.0', '2_0']),
    'DOTA_GSD_2025_03': product(['dota', 'DOTA'], ['_gsd_2025_03', '_GSD_2025_03', '_gsd_202503', '_GSD_202503']),
    'DIOR': ['dior', 'DIOR'],
    'HRSC': product(['hrsc', 'HRSC'], ['', '2016']),
    'HRSC_cls': product(['hrsc', 'HRSC'], ['_cls', '2016_cls']),
    'MSRA_TD500': ['msra_td500', 'MSRA_TD500', 'msra-td500', 'MSRA-TD500'],
    'HUST_TR400': ['hust_tr500', 'HUST_TR400', 'hust-tr400', 'HUST-TR400'],
    'RCTW_17': ['rctw_17', 'RCTW_17', 'rctw-17', 'RCTW-17'],
    'SynthText': ['synthtext', 'SynthText'],
    'ICDAR2015': ['ICDAR2015', 'icdar2015'],
    'VOC': ['VOC', 'voc'],
}

img_exts = ['.jpg', '.JPG', 'jpeg', '.png', '.tif', '.tiff', '.bmp']


def read_img_info(imgpath):
    imgfile = osp.split(imgpath)[-1]
    img_id, ext = osp.splitext(imgfile)
    if ext not in img_exts:
        return None

    width, height = imsize(imgpath)
    content = dict(width=width, height=height, filename=imgfile, id=img_id)
    return content


def get_classes(alias_or_list):
    if isinstance(alias_or_list, str):
        if osp.isfile(alias_or_list):
            class_names = []
            with open(alias_or_list) as f:
                for line in f:
                    class_names.append(line.strip())
            return tuple(class_names)

        for k, v in dataset_aliases.items():
            if alias_or_list in v:
                return dataset_classes[k]

        return alias_or_list.split('|')

    if isinstance(alias_or_list, (list, tuple)):
        classes = []
        for item in alias_or_list:
            for k, v in dataset_aliases.items():
                if item in v:
                    classes.extend(dataset_classes[k])
                    break
            else:
                classes.append(item)
        return tuple(classes)

    raise TypeError(
        f'input must be a str, list or tuple but got {type(alias_or_list)}')


def change_cls_order(contents, old_classes, new_classes):
    if isinstance(new_classes, str):
        new_classes = get_classes(new_classes)
    for n_c, o_c in zip(new_classes, old_classes):
        if n_c != o_c:
            break
    else:
        if len(old_classes) == len(new_classes):
            return

    new_cls2lbl = {cls: i for i, cls in enumerate(new_classes)}
    lbl_mapper = [new_cls2lbl[cls] if cls in new_cls2lbl else -1
                  for cls in old_classes]
    lbl_mapper = np.array(lbl_mapper, dtype=np.int64)

    for content in contents:
        new_labels = lbl_mapper[content['ann']['labels']]
        if (new_labels == -1).any():
            inds = np.nonzero(new_labels != -1)[0]
            for k, v in content['ann'].items():
                try:
                    content['ann'][k] = v[inds]
                except TypeError:
                    content['ann'][k] = [v[i] for i in inds]
            content['ann']['labels'] = new_labels[new_labels != -1]
        else:
            content['ann']['labels'] = new_labels


def remove_cls_from(contents, old_classes, to_remove):
    """
    Remove specified class(es) from annotations and update remaining class labels.
    
    Args:
        contents: List of dicts where each dict contains an 'ann' key with annotations.
                 Each 'ann' should contain 'labels' (class indices) and other annotation fields.
        old_classes: List of original class names/IDs.
        to_remove: Class name or list of class names to remove.
    
    Returns:
        Updated contents with specified classes removed and labels reindexed.
        New list of class names with removed classes excluded.
    """
    # Convert single class to list for uniform handling
    if isinstance(to_remove, str):
        to_remove = [to_remove]
    
    # Create new class list by removing specified classes
    new_classes = [cls for cls in old_classes if cls not in to_remove]
    
    # Early exit if nothing to remove
    if len(new_classes) == len(old_classes):
        return contents, old_classes
    
    # Create mapping from old class indices to new indices (-1 for removed classes)
    cls_to_new_idx = {cls: idx for idx, cls in enumerate(new_classes)}
    label_mapper = np.array([
        cls_to_new_idx.get(cls, -1) for cls in old_classes
    ], dtype=np.int64)
    
    # Process each content item
    for content in contents:
        ann = content['ann']
        old_labels = ann['labels']
        new_labels = label_mapper[old_labels]
        
        # Find indices of annotations to keep (where label != -1)
        keep_mask = (new_labels != -1)
        keep_indices = np.nonzero(keep_mask)[0]
        
        # Filter all annotation fields
        for key, value in content['ann'].items():
            try:
                # For array-like values
                content['ann'][key] = value[keep_indices]
            except TypeError:
                # For list-like values
                content['ann'][key] = [value[i] for i in keep_indices]
        # Update labels
        content['ann']['labels'] = new_labels[keep_mask]
    
    return contents, new_classes


def merge_prior_contents(bases, priors, merge_type='addition'):
    id_mapper = {base['id']: i for i, base in enumerate(bases)}
    for prior in priors:
        img_id = prior['id']
        if img_id not in id_mapper:
            continue

        base = bases[id_mapper[img_id]]
        for key in prior.keys():
            if key in ['id', 'filename', 'width', 'height', 'ann']:
                continue
            if (key not in base) or (base[key] is None) or (merge_type == 'replace'):
                base[key] = prior[key]

        if 'ann' in prior:
            if not base.get('ann', {}):
                base['ann'] = prior['ann']
            else:
                base_anns, prior_anns = base['ann'], prior['ann']
                assert base_anns.keys() == prior_anns.keys()
                for key in prior_anns:
                    if isinstance(base_anns[key], np.ndarray):
                        base_anns[key] = prior_anns[key] if merge_type == 'replace' \
                                else np.concatenate([base_anns[key], prior_anns[key]], axis=0)
                    elif isinstance(base_anns[key], list):
                        base_anns[key] = prior_anns[key] if merge_type == 'replace' \
                                else base_anns[key].update(prior_anns[key])
                    else:
                        raise TypeError("annotations only support np.ndarrya and list"+
                                        f", but get {type(base_anns[key])}")


def split_imgset(contents, imgset):
    id_mapper = {content['id']: i for i, content in enumerate(contents)}
    assert isinstance(imgset, (list, tuple, str))
    if isinstance(imgset, str):
        with open(imgset, 'r') as f:
            imgset = [line for line in f]

    imgset_contents = []
    for img_id in imgset:
        img_id = osp.split(img_id.strip())[-1]
        img_id = osp.splitext(img_id)[0]
        if img_id not in id_mapper:
            print(f"Can't find ID:{img_id} image!")
            continue

        imgset_contents.append(contents[id_mapper[img_id]])
    return imgset_contents


def nproc_map(func, tasks, nproc):
    if nproc > 1:
        pool = Pool(nproc)
        iterator = pool.imap(func, tasks)
    else:
        iterator = map(func, tasks)

    contents = [c for c in iterator if c is not None]

    if nproc > 1:
        pool.close()
    return contents


def prog_map(func, tasks, nproc):
    if nproc > 1:
        pool = Pool(nproc)
        iterator = pool.imap(func, tasks)
    else:
        iterator = map(func, tasks)

    contents = []
    with tqdm(total=len(tasks)) as pbar:
        for content in iterator:
            pbar.update()
            if content is not None:
                contents.append(content)

    if nproc > 1:
        pool.close()
    return contents


class _ConstMapper:

    def __init__(self, const_value):
        self.const_value = const_value

    def __getitem__(self, key):
        return self.const_value

    def __contains__(self, key):
        return True
