# reference: https://zenn.dev/ryo_tan/articles/5d03c0157501aa
# this file is the replica of run.ipynb
# it's easy to debug code in .py and run long running code here.

import os
import sys
if not 'Informer' in sys.path:
    sys.path += ['Informer']

from utils.tools import dotdict
from exp.exp_informer import Exp_Informer
import torch

from torch.utils.data import DataLoader
from data.data_loader import Dataset_Pred
from torch.utils.data import DataLoader
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import json
import time
import shutil
import matplotlib.pyplot as plt

def remove_directory(dir_path):
    if os.path.exists(dir_path):
        print('removing directory ', dir_path)
        shutil.rmtree(dir_path)

def make_directory(dir_path):
    if not os.path.exists(dir_path):
        print('creating dir ', dir_path)
        os.mkdir(dir_path)

def plot_predictions(trues, preds, start_index, step, num_plots, setting, root_path):
        num_rows = num_plots // 3
        num_cols = 3

        fig, axes = plt.subplots(num_rows, num_cols, figsize=(14, 3 * num_rows), sharex=True, sharey=True)

        for i, ax in enumerate(axes.flatten()):
            if i < num_plots:
                index = start_index + i * step

                ax.plot(trues[index, :, -1], label='GroundTruth')
                ax.plot(preds[index, :, -1], label='Prediction')

                ax.set_title(f'Index {index}')
                ax.legend()
                ax.set_xlabel('time')
                ax.set_ylabel('Realized volatility')
                ax.tick_params(axis='both', which='both', labelsize=8, direction='in')

            else:
                ax.axis('off')


        plt.tight_layout()
        make_directory(os.path.join(root_path, "results_informer"))
        make_directory(os.path.join(root_path, "results_informer", setting))
        plt.savefig(os.path.join(root_path, 'results_informer/'+setting+'/prediction_plot.png'))
        plt.show()
        

def run_volatility(args):    
    args.model = 'informer' # model of experiment, options: [informer, informerstack, informerlight(TBD)]
    args.data = 'custom' # data
    # args.root_path =  ROOT_DIR#'/content/' # root path of data file
    args.freq = '1m' # freq for time features encoding, options:[s:secondly, t:minutely, h:hourly, d:daily, b:business days, w:weekly, m:monthly], you can also use more detailed freq like 15min or 3h
    args.checkpoints = './informer_checkpoints' # location of model checkpoints
    args.seq_len = 96 # input sequence length of Informer encoder
    args.label_len = 48 # start token length of Informer decoder
    args.pred_len = 24 # prediction sequence length
    # Informer decoder input: concat[start token series(label_len), zero padding series(pred_len)]
    args.enc_in = 8 # encoder input size
    args.dec_in = 8 # decoder input size
    args.c_out = 8 # output size
    args.factor = 1 # probsparse attn factor
    args.d_model = 512 # dimension of model
    args.n_heads = 8 # num of heads
    args.d_ff = 2048 # dimension of fcn in model
    args.dropout = 0.05 # dropout
    args.attn = 'prob' # attention used in encoder, options:[prob, full]
    args.embed = 'fixed' # time features encoding, options:[timeF, fixed, learned]
    args.activation = 'gelu' # activation
    args.distil = True # whether to use distilling in encoder
    args.output_attention = False # whether to output attention in ecoder
    args.mix = True
    args.padding = 0
    args.freq = 'h'
    args.batch_size = 32
    args.loss = 'mse'
    args.lradj = 'type1'
    args.use_amp = False # whether to use automatic mixed precision training
    args.num_workers = 0
    args.itr = 1
    args.patience = 100
    args.des = 'exp'
    args.use_gpu = True if torch.cuda.is_available() else False
    args.gpu = 0
    args.use_multi_gpu = False
    args.devices = '0,1,2,3'
    args.use_gpu = True if torch.cuda.is_available() and args.use_gpu else False
    args.inverse = True

    if args.use_gpu and args.use_multi_gpu:
        args.devices = args.devices.replace(' ','')
        device_ids = args.devices.split(',')
        args.device_ids = [int(id_) for id_ in device_ids]
        args.gpu = args.device_ids[0]

    # Set augments by using data name
    data_parser = {
        'custom':{'data':args.data_path,
                'T':args.target,
                'M': args.target_config_list_m,
                'S':[1,1,1],
                'MS': args.target_config_list_ms}, #Change the array here based on the number of features
    }
    if args.data in data_parser.keys():
        data_info = data_parser[args.data]
        args.data_path = data_info['data']
        args.target = data_info['T']
        args.enc_in, args.dec_in, args.c_out = data_info[args.features]

    args.detail_freq = args.freq
    args.freq = args.freq[-1:]

    Exp = Exp_Informer
    print('Args in experiment:')
    print(args)

    error_mertics = {}
    losses = None
    setting = ''
    for ii in range(args.itr):
        # setting record of experiments
        setting = '{}_{}_{}_ft{}_sl{}_ll{}_pl{}_dm{}_nh{}_el{}_dl{}_df{}_at{}_fc{}_eb{}_dt{}_mx{}_{}_{}'.format(
                    args.model_id,
                    args.model, args.data, args.features,
                    args.seq_len, args.label_len, args.pred_len,
                    args.d_model, args.n_heads, args.e_layers, args.d_layers, args.d_ff, args.attn, 
                    args.factor, args.embed, args.distil, args.mix, args.des, ii)

        # set experiments
        exp = Exp(args)

        # train
        print('>>>>>>>start training : {}>>>>>>>>>>>>>>>>>>>>>>>>>>'.format(setting))
        model, losses = exp.train(setting)

        # test
        print('>>>>>>>testing : {}<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<'.format(setting))
        error_mertics = exp.test(setting)

        print('Finished training')

    print('setting folder ', setting)
    # If you already have a trained model, you can set the arguments and model path, then initialize a Experiment and use it to predict
    # Prediction is a sequence which is adjacent to the last date of the data, and does not exist in the data
    # If you want to get more information about prediction, you can refer to code `exp/exp_informer.py function predict()` and `data/data_loader.py class Dataset_Pred`

    exp = Exp(args)

    exp.predict(setting, True)

    prediction = np.load('./results/'+setting+'/real_prediction.npy')

    prediction.shape

    Data = Dataset_Pred
    timeenc = 0 if args.embed!='timeF' else 1
    flag = 'pred'; shuffle_flag = False; drop_last = False; batch_size = 1

    freq = args.detail_freq

    data_set = Data(
        root_path=args.root_path,
        is_time_id=args.is_time_id,
        data_path=args.data_path,
        flag=flag,
        size=[args.seq_len, args.label_len, args.pred_len],
        features=args.features,
        target=args.target,
        timeenc=timeenc,
        freq=freq
    )
    data_loader = DataLoader(
        data_set,
        batch_size=batch_size,
        shuffle=shuffle_flag,
        num_workers=args.num_workers,
        drop_last=drop_last)

    len(data_set), len(data_loader)

    # When we finished exp.train(setting) and exp.test(setting), we will get a trained model and the results of test experiment
    # The results of test experiment will be saved in ./results/{setting}/pred.npy (prediction of test dataset) and ./results/{setting}/true.npy (groundtruth of test dataset)

    preds = np.load('./results/'+setting+'/pred.npy')
    trues = np.load('./results/'+setting+'/true.npy')

    # [samples, pred_len, dimensions]
    preds.shape, trues.shape

    plot_predictions(trues, preds, start_index=0, step=50, num_plots=6, setting = setting, root_path=args.root_path)

    return error_mertics, losses, setting

def drawplots(epochs, train_loss, validation_loss, test_loss,title, setting, root_path):
    plt.plot(epochs, train_loss, label="train")
    plt.plot(epochs, validation_loss, label="validation")
    plt.plot(epochs, test_loss, label="test")
    plt.title(title)
    plt.legend()
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    make_directory(os.path.join(root_path, "results_informer"))
    make_directory(os.path.join(root_path, "results_informer", setting))
    plt.savefig(os.path.join(root_path, 'results_informer', setting, title + '.png'))
    plt.show()
    
def drawplot(epochs, losses, title, setting, root_path):
    plt.plot(epochs, losses)
    plt.title(title)
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    make_directory(os.path.join(root_path, "results_informer"))
    make_directory(os.path.join(root_path, "results_informer", setting))
    plt.savefig(os.path.join(root_path, 'results_informer', setting, title + '.png'))
    plt.show()

def run_experiments(run, run_type):
    # run 1
    args = dotdict()
    args.target_config_list_ms = []
    args.e_layers = 2 # num of encoder layers
    args.d_layers = 1 # num of decoder layers
    args.learning_rate = 0.00001 # 0.0001
    args.train_epochs = 20
    args.model_id = run_type + "_" + run
    args.root_path = "/Users/pujanmaharjan/uni adelaide/research project/realized-volatility/data/"

    error_metrics_all = []
    losses_all = []
    setting = ""

    # Run 1
    if run == "targets":
        args.data_path = 'stocks_targets_0.csv' #'output.csv' # data file
        args.target = 'target' # target feature in S or MS task
        args.features = 'S' # forecasting task, options:[M, S, MS];
                                #M:multivariate predict multivariate, S:univariate predict univariate,
                                #MS:multivariate predict univariate
        m_feature_count = len(pd.read_csv(os.path.join(args.root_path, args.data_path)).columns) - 1
        args.target_config_list_m = [m_feature_count, m_feature_count, 1]
        args.is_time_id = True
        
        error_metrics_targets, losses_run_1, setting = run_volatility(args)
        error_metrics_all.append(error_metrics_targets)
        losses_all.append(losses_run_1)

    # run 2
    if run == "tcn_targets":
        if run_type == "similar":
            args.data_path = 'similar_stock_data_tcn_targets.csv'
        elif run_type == "dissimilar":
            args.data_path = 'dissimilar_stock_data_tcn_targets.csv'
        else:
            args.data_path ='stock_data_tcn_targets.csv'
        args.target = 'stock_0_y' # target feature in S or MS task
        args.features = 'M'
        feature_count = len(pd.read_csv(os.path.join(args.root_path, args.data_path)).columns) - 1
        args.target_config_list_m = [feature_count, feature_count, feature_count]
        args.is_time_id = True
        error_metrics_tcn, losses_run_2, setting = run_volatility(args)
        error_metrics_all.append(error_metrics_tcn)
        losses_all.append(losses_run_2)

    # run 3
    if run == "features":
        args.data_path = 'stock_data_basic_features_stock_0.csv' #'output.csv' # data file
        args.target = 'target' # target feature in S or MS task
        args.features = 'MS'
        feature_count = len(pd.read_csv(os.path.join(args.root_path, args.data_path)).columns) - 1
        args.target_config_list_ms = [feature_count,feature_count,1]
        args.is_time_id = True
        error_metrics_features, losses_run_3, setting = run_volatility(args)
        error_metrics_all.append(error_metrics_features)
        losses_all.append(losses_run_3)

    print('error metrics all ', error_metrics_all)
    error_metrics_df = pd.DataFrame(error_metrics_all)
    print(error_metrics_df)
    error_metrics_df.to_csv(os.path.join(args.root_path, 'results_informer',setting,'error_metrics.csv'), index=False)

    losses_df = pd.DataFrame(losses_all[0])
    losses_df.to_csv(os.path.join(args.root_path, 'results_informer', setting, 'losses.csv'), index=False)

    # print(losses)
    first_loss = losses_all[0]
    print(first_loss)
    epochs = [f['epoch'] for f in first_loss]
    print(epochs)
    train_losses = [f['train_loss'] for f in first_loss]
    validation_losses = [f['validation_loss'] for f in first_loss]
    test_losses = [f['test_loss'] for f in first_loss]


    drawplots(epochs, train_losses, validation_losses, test_losses, 'Loss curves', setting, args.root_path)
    drawplot(epochs, train_losses, 'Train loss', setting, args.root_path)
    drawplot(epochs, validation_losses, 'Validation loss', setting, args.root_path)
    drawplot(epochs, test_losses, 'Test loss', setting, args.root_path)

run_experiments("tcn_targets", "similar")