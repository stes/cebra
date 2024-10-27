#
# CEBRA: Consistent EmBeddings of high-dimensional Recordings using Auxiliary variables
# © Mackenzie W. Mathis & Steffen Schneider (v0.4.0+)
# Source code:
# https://github.com/AdaptiveMotorControlLab/CEBRA
#
# Please see LICENSE.md for the full license document:
# https://github.com/AdaptiveMotorControlLab/CEBRA/blob/main/LICENSE.md
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Generate synthetic datasets for benchmarking embedding quality.

References:
    Adapted from pi-VAE: https://github.com/zhd96/pi-vae/blob/main/code/pi_vae.py
"""
import argparse
import pathlib

import joblib as jl
import keras
import numpy as np
import poisson
import scipy.stats
import tensorflow as tf

import third_party.pivae.pivae_code.pi_vae as pi_vae


def simulate_cont_data_diff_var(length: int, n_dim: int, noise_func: str):
    """Generate a synthetic dataset with the chosen generative process.

    Adapted from pi-VAE; https://github.com/zhd96/pi-vae/blob/main/code/pi_vae.py.
    The 1D continuous label u is sampled from uniform distribution defined in [0, 2*pi].
    The corresponding 2D latent z is sampled from a normal distribution defined by the mean (u, 2*sin(u)) and the variance (0.6-0.3*|sin(u)|, 0.3*|sin(u)|).
    The `n_dim` firing rate is generated by feeding z into bijective mixing function modeled by RealNVP.
    Finally, observation X is generated by adding noise of the choice.

    Args:
        length: The length of the simulation or the number of the simulated samples.
        n_dim: The dimension of the observation.
        noise_func: The distribution used for generative process
    """
    ## simulate 2d z
    np.random.seed(777)

    u_true = np.random.uniform(0, 2 * np.pi, size=[length, 1])
    mu_true = np.hstack((u_true, 2 * np.sin(u_true)))
    var_true = 0.15 * np.abs(mu_true)
    var_true[:, 0] = 0.6 - var_true[:, 1]
    z_true = np.random.normal(0, 1, size=[length, 2
                                         ]) * np.sqrt(var_true) + mu_true
    z_true = np.hstack((z_true, np.zeros((z_true.shape[0], n_dim - 2))))

    ## simulate mean
    dim_x = z_true.shape[-1]
    permute_ind = []
    n_blk = 4
    for ii in range(n_blk):
        np.random.seed(ii)
        permute_ind.append(tf.convert_to_tensor(np.random.permutation(dim_x)))

    x_input = keras.layers.Input(shape=(dim_x,))
    x_output = pi_vae.realnvp_block(x_input)
    for ii in range(n_blk - 1):
        x_output = keras.layers.core.Lambda(pi_vae.perm_func,
                                            arguments={"ind": permute_ind[ii]
                                                      })(x_output)
        x_output = pi_vae.realnvp_block(x_output)

    realnvp_model = keras.models.Model(inputs=[x_input], outputs=x_output)
    mean_true = realnvp_model.predict(z_true)
    lam_true = np.exp(2.2 * np.tanh(mean_true))
    if noise_func is not None:
        x = noise_func(lam_true)
        return z_true, u_true, mean_true, lam_true, x
    else:
        return z_true, u_true, mean_true, lam_true


__noises = {}


def _register_noise(func):
    __noises[func.__name__] = func
    return func


@_register_noise
def poisson(x):
    """Apply poisson noise to the input.

    This setup corresponds to the synthetic dataset originally
    considered by Zhou and Wei (NeurIPS 2021) for pi-VAE benchmarking.

    Args:
        x: The rate parameter

    Returns:
        Samples with the specified rate, of same shape as the input.
    """
    return np.random.poisson(x)


@_register_noise
def gaussian(x):
    """Apply truncated Gaussian noise with unit variance to the input.

    Args:
        x: The mean

    Returns:
        The samples, of same shape as the input.
    """
    return scipy.stats.truncnorm.rvs(0, 1000, loc=x)


@_register_noise
def laplace(x):
    """Apply (post-truncated) Laplace noise to the input.

    Args:
        x: The mean

    Returns:
        The samples, of same shape as the input.
    """
    return np.clip(np.random.laplace(x), a_min=0, a_max=1000)


@_register_noise
def uniform(x):
    """Apply uniform noise from [0, 2) to the input.

    Args:
        x: The offset added to the noise samples.

    Returns:
        The samples, of same shape as the input.
    """
    return np.random.uniform(0, 2, x.shape) + x


@_register_noise
def t(x):
    """Apply student-t distributed noise to the input.

    Args:
        x: The mean

    Returns:
        The samples, of same shape as the input.
    """
    return scipy.stats.distributions.t.rvs(2, loc=x)


@_register_noise
def refractory_poisson(x):
    """TODO. Not implemented yet."""
    raise NotImplementedError()


if __name__ == "__main__":
    """Generate synthetic datasets with poisson, gaussian, laplace, uniform, t noise during generative process."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--save-path",
        type=str,
        default="/data/synthetic/",
        help="Directory to save the generated dataset.",
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=15000,
        help="The number of the trials to generate",
    )
    parser.add_argument("--neurons",
                        type=int,
                        default=100,
                        help="The number of the neurons")
    parser.add_argument(
        "--noise",
        type=str,
        choices=list(__noises.keys()),
        help="The type of noise to add in the generative process",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=50,
        help=
        "The scaling factor to firing rate for generating poisson neurons with refractory period",
    )
    parser.add_argument(
        "--time-interval",
        type=float,
        default=3,
        help=
        "The time interval (sec) to sample spikes for generating poisson neurons with refractory period",
    )
    parser.add_argument(
        "--refractory-period",
        type=float,
        default=0.01,
        help="The refaractory period (sec) of neurons",
    )

    args = parser.parse_args()

    if args.noise != "refractory_poisson":
        func = __noises[args.noise]
        z_true, u_true, mean_true, lam_true, x = simulate_cont_data_diff_var(
            args.n_samples, args.neurons, func)
    else:
        z_true, u_true, mean_true, lam_true = simulate_cont_data_diff_var(
            args.n_samples, args.neurons, None)
        flattened_lam = lam_true.flatten()
        x = np.zeros_like(flattened_lam)
        for i, rate in enumerate(flattened_lam):
            neuron = poisson.PoissonNeuron(
                spike_rate=rate * args.scale,
                num_repeats=1,
                time_interval=args.time_interval,
            )
            count = neuron._get_counts(refractory_period=args.refractory_period)
            x[i] = count
        x = x.reshape(lam_true.shape)

    jl.dump(
        {
            "z": z_true,
            "u": u_true,
            "lam": lam_true,
            "x": x
        },
        pathlib.Path(args.save_path) / f"continuous_label_{args.noise}.jl",
    )
