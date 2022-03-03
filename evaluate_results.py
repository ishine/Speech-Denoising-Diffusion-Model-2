import torch
from pathlib import Path
from data_loader.data_loaders import OutputDataset
from torchmetrics.audio.pesq import PerceptualEvaluationSpeechQuality
from torchmetrics.audio.si_snr import ScaleInvariantSignalNoiseRatio
from torchmetrics.audio.stoi import ShortTimeObjectiveIntelligibility
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np
import argparse
from parse_config import ConfigParser


def main(results_path, config):

    samples_path = Path(results_path)/'samples'

    datatype = config['infer_dataset']['args']['datatype']
    sample_rate = config['sample_rate']


    metrics = {'pesq_wb', 'sisnr', 'stoi'}
    evaluate(samples_path, datatype, sample_rate, metrics)

def evaluate(samples_path, datatype, sample_rate, metrics):

    output_dataset = OutputDataset(samples_path, datatype, sample_rate)

    len_data = len(output_dataset)
    evaluator = {'pesq_wb': PerceptualEvaluationSpeechQuality(sample_rate, 'wb'),
                 'pesq_nb': PerceptualEvaluationSpeechQuality(sample_rate, 'nb'),
                 'sisnr': ScaleInvariantSignalNoiseRatio(),
                 'stoi': ShortTimeObjectiveIntelligibility(sample_rate)}

    noisy_metrics_vec = torch.zeros(len(metrics), len_data)
    output_metrics_vec = torch.zeros(len(metrics), len_data)

    for i in tqdm(range(len_data)):
        clean, noisy, output = output_dataset.__getitem__(i)
        for j, m in enumerate(metrics):
            try:
                output_metrics_vec[j, i] = evaluator[m](output, clean)
                noisy_metrics_vec[j, i] = evaluator[m](noisy, clean)
            except:
                print(output_dataset.getName(i))

    for j, m in enumerate(metrics):
        print('Average {} for output: {}'.format(m, torch.mean(output_metrics_vec[j, :])))
        print('Average {} for noisy: {}'.format(m, torch.mean(noisy_metrics_vec[j, :])))
        torch.save(output_metrics_vec[j, :], samples_path/'output_{}.pt'.format(m))
        torch.save(noisy_metrics_vec[j, :], samples_path/'noisy_{}.pt'.format(m))


def loadResults(samples_path, datatype, sample_rate, metrics):
    # load and show results

    output_dataset = OutputDataset(samples_path, datatype, sample_rate)

    for j, m in enumerate(metrics):

        output_temp = torch.load(samples_path/'output_{}.pt'.format(m))
        noisy_temp = torch.load(samples_path/'noisy_{}.pt'.format(m))
        improvement = output_temp - noisy_temp
        print('Average {} for output: {}'.format(m, torch.mean(output_temp[:])))
        print('Average {} for noisy: {}'.format(m, torch.mean(noisy_temp[:])))
        (max_improve, max_idx) = improvement.max(0)
        print('Max improvement for {}: {}, index: {}'.format(m, max_improve, max_idx))

        clean, noisy, output = output_dataset.__getitem__(max_idx)
        t = np.arange(clean.shape[-1], dtype=np.float64)/sample_rate
        fig, axs = plt.subplots(3,1, sharex=True)
        plt.subplots_adjust(hspace=0.4)
        axs[0].plot(t, clean.numpy().T, linewidth=0.5)
        axs[0].set_ylabel('Amplitude')
        axs[0].set_title('Clean Speech')

        axs[1].set_ylabel('Amplitude')
        axs[1].plot(t, noisy.numpy().T, linewidth=0.5)
        axs[1].set_title('Noisy Speech')
        axs[2].set_xlabel('Time, s')
        axs[2].set_ylabel('Amplitude')
        axs[2].plot(t, output.numpy().T, linewidth=0.5)
        axs[2].set_title('De-noised Speech')
        plt.show(block=False)

    plt.show()



if __name__ == '__main__':
    args = argparse.ArgumentParser(description='PyTorch Template')
    args.add_argument('path', type=str,
                      help = 'result path')

    args = args.parse_args()

    args.config = Path(args.path)/'config.json'
    args.device = None
    args.resume = None

    config = ConfigParser.from_args(args)
    main(args.path, config)

