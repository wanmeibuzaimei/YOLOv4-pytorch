from torch.utils.data import DataLoader
import utils.gpu as gpu
from model.build_model import Build_Model
from tqdm import tqdm
from utils.tools import *
from eval.evaluator import Evaluator
import argparse
import time
import logging
import config.yolov4_config as cfg
from utils.visualize import *
from utils.torch_utils import *
from utils.log import Logger
from tensorboardX import SummaryWriter
# import os
# os.environ["CUDA_VISIBLE_DEVICES"]='0'


class Evaluation(object):
    def __init__(self,
                 gpu_id=0,
                 weight_path=None,
                 img_size=544,
                 visiual=None,
                 eval=False,
                 ):
        self.img_size = img_size
        self.__num_class = cfg.VOC_DATA["NUM"]
        self.__conf_threshold = cfg.VAL["CONF_THRESH"]
        self.__nms_threshold = cfg.VAL["NMS_THRESH"]
        self.__device = gpu.select_device(gpu_id)
        self.__multi_scale_val = cfg.VAL["MULTI_SCALE_VAL"]
        self.__flip_val = cfg.VAL["FLIP_VAL"]

        self.__visiual = visiual
        self.__eval = eval
        self.__classes = cfg.VOC_DATA["CLASSES"]

        self.__model = Build_Model().to(self.__device)

        self.__load_model_weights(weight_path)

        self.__evalter = Evaluator(self.__model, showatt=False)

    def __load_model_weights(self, weight_path):
        print("loading weight file from : {}".format(weight_path))

        weight = os.path.join(weight_path)
        chkpt = torch.load(weight, map_location=self.__device)
        self.__model.load_state_dict(chkpt)
        print("loading weight file is done")
        del chkpt


    def val(self):
        global writer, logger
        if self.__eval:
            logger.info("***********Start Evaluation****************")
            start = time.time()
            mAP = 0
            with torch.no_grad():
                    Recalls, Precisions, APs = Evaluator(self.__model, showatt=False).APs_voc(self.__multi_scale_val, self.__flip_val)
                    for i in APs:
                        logger.info("{} --> mAP : {}".format(i, APs[i]))
                        mAP += APs[i]
                    mAP = mAP / self.__num_class
                    logger.info('mAP:{}'.format(mAP))
            end = time.time()
            logger.info("  ===val cost time:{:.4f}s".format(end - start))

    def detection(self):
        global writer, logger
        if self.__visiual:
            imgs = os.listdir(self.__visiual)
            logger.info("***********Start Detection****************")
            start = time.clock()
            for v in imgs:
                path = os.path.join(self.__visiual, v)
                logger.info("val images : {}".format(path))

                img = cv2.imread(path)
                assert img is not None

                bboxes_prd = self.__evalter.get_bbox(img,v)
                if bboxes_prd.shape[0] != 0:
                    boxes = bboxes_prd[..., :4]
                    class_inds = bboxes_prd[..., 5].astype(np.int32)
                    scores = bboxes_prd[..., 4]

                    visualize_boxes(image=img, boxes=boxes, labels=class_inds, probs=scores, class_labels=self.__classes)
                    path = os.path.join(cfg.PROJECT_PATH, "detection_result/{}".format(v))

                    cv2.imwrite(path, img)
                    logger.info("saved images : {}".format(path))
            end = time.clock()
            times = end - start
            FPS = len(imgs) / times
            logger.info('FPS:{}'.format(FPS))
            logger.info("  ===detection cost time:{:.4f}s".format(times))


if __name__ == "__main__":
    global logger, writer
    parser = argparse.ArgumentParser()
    parser.add_argument('--weight_path', type=str, default='E:\YOLOV4\weight/best.pt', help='weight file path')
    parser.add_argument('--log_val_path', type=str, default='log_val',
                        help='weight file path')
    parser.add_argument('--gpu_id', type=int, default=-1, help='whither use GPU(eg:0,1,2,3,4,5,6,7,8) or CPU(-1)')
    parser.add_argument('--visiual', type=str, default='E:\YOLOV4/test_pic', help='val data path or None')
    parser.add_argument('--eval', action='store_true', default=True, help='eval the mAP or not')
    parser.add_argument('--mode', type=str, default='det',
                        help='val or det')
    opt = parser.parse_args()
    writer = SummaryWriter(logdir=opt.log_val_path + '/event')
    logger = Logger(log_file_name=opt.log_val_path + '/log_val.txt', log_level=logging.DEBUG, logger_name='CIFAR').get_log()

    if opt.mode == 'val':
        Evaluation(gpu_id=opt.gpu_id,
                    weight_path=opt.weight_path,
                   eval=opt.eval,
                   visiual=opt.visiual).val()
    else:
        Evaluation(gpu_id=opt.gpu_id,
                    weight_path=opt.weight_path,
                   eval=opt.eval,
                   visiual=opt.visiual).detection()

