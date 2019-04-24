# Reference Paper: Prototypical Networks for Few shot Learning in PyTorch
# Reference Paper URL: https://arxiv.org/pdf/1703.05175v2.pdf
# Reference Paper Authors: Jake Snell, Kevin Swersky, Richard S. Zemel

# Reference Code: https://github.com/orobix/Prototypical-Networks-for-Few-shot-Learning-PyTorch
# Reference Code Author: Daniele E. Ciriello

import torch
from torch.nn import functional as F, CrossEntropyLoss
from torch.nn.modules import Module

class PrototypicalLoss(Module):
    '''
    Loss class deriving from Module for the prototypical loss function defined below
    '''
    def __init__(self, n_support):
        super(PrototypicalLoss, self).__init__()
        self.n_support = n_support

    def forward(self, input, target):
        return prototypical_loss(input, target, self.n_support)


def euclidean_dist(x, y):
    '''
    Compute euclidean distance between two tensors
    '''
    # x: N x D
    # y: M x D
    n = x.size(0)
    m = y.size(0)
    d = x.size(1)
    if d != y.size(1):
        raise Exception

    x = x.unsqueeze(1).expand(n, m, d)
    y = y.unsqueeze(0).expand(n, m, d)

    return torch.pow(x - y, 2).sum(2)


def prototypical_loss(device, n_classes, n_query, prototypes, query_samples):
    '''
    Inspired by https://github.com/jakesnell/prototypical-networks/blob/master/protonets/models/few_shot.py
    Compute the prototypes by averaging the features of n_support
    samples for each class in target, computes then the distances from each
    samples' features to each one of the prototypes, computes the
    log_probability for each n_query samples for each one of the current
    classes, of appartaining to a class c, loss and accuracy are then computed
    and returned
    '''
    dists = euclidean_dist(query_samples, prototypes)

    log_p_y = F.log_softmax(-dists, dim=1).view(n_classes, n_query, -1)
    log_p_y = log_p_y.to(device)

    target_inds = torch.arange(0, n_classes)
    target_inds = target_inds.view(n_classes, 1, 1)
    target_inds = target_inds.expand(n_classes, n_query, 1).long()
    target_inds = target_inds.to(device)
    
    loss_val = -log_p_y.gather(2, target_inds).squeeze().view(-1).mean()
    _, y_hat = log_p_y.max(2)
    acc_val = y_hat.eq(target_inds.squeeze()).float().mean()

    return loss_val,  acc_val

def gaussian_prototypical_loss(device, n_classes, n_query, prototypes, query_samples, support_inv_sigmas, criterion):
    # query samples 300 x 128
    # prototypes 60 x 64
    # sigmas 60 x 64
    dists = gaussian_dist(query_samples, prototypes, support_inv_sigmas) # [60, 5]
    log_p_y = F.log_softmax(-dists, dim=1).view(n_classes, n_query, -1)
    log_p_y = log_p_y.to(device)

    target_inds = torch.arange(0, n_classes)
    target_inds = target_inds.view(n_classes, 1, 1)
    target_inds = target_inds.expand(n_classes, n_query, 1).long()
    target_inds = target_inds.to(device)
    
    loss = -log_p_y.gather(2, target_inds).squeeze().view(-1).mean()
    _, y_hat = log_p_y.max(2)
    acc = y_hat.eq(target_inds.squeeze()).float().mean()
    # y_predicted = torch.argmin(dists, dim=0)
    # y_target = torch.ones(query_samples.size(0))
    # for i in range(n_classes):
    #     y_target[n_query*i:n_query*(i+1)] *= i
    # y_target = y_target.long()

    # loss = criterion(-dists.transpose(0, 1), y_target)
    # acc = y_predicted.eq(y_target).float().mean()

    return loss,  acc

def gaussian_dist(x, y, sigmas, mode="radial"):
    n_points = x.size(0)
    n_classes = y.size(0)
    n_dim_x = x.size(0)
    n_dim = y.size(1)
    n_query_samples = int(n_points / n_classes)
    # x size: 300, 128
    # y size: 60 64
    #sigmas size: 60 64
    if mode == "diagonal":
        x_encoded, _ = torch.split(x, int(x.size(1)/2), dim=1)
    elif mode == "radial":
        x_encoded = x[:, :int(x.size(1) - 1)]
    dists = torch.empty((n_dim_x, n_classes))
    for i in range(n_classes):
        delta = x_encoded - y[i] # [300, 64]
        dist = delta * torch.sqrt(sigmas[i, :].unsqueeze(0))
        dists[:, i] = torch.norm(dist, dim=1)
    return dists
