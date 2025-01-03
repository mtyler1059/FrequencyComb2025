import argparse
import csv
import numpy as np
import pandas as pd

# Define comb creation functions
def comb_x(cps1):
  comb_x_values = np.fft.fftfreq(n = int(cps1['time'] * cps1['sample_rate']), d = 1 / cps1['sample_rate'])
  return comb_x_values

def calculate_h(cps2, comb_x_values_i):
  path_length = 100e-3
  speed_of_light = 3e8
  refractive_index = cps2['n_0']
  absorption_coefficient = cps2['alpha_0']
  refractive_index_transformed = refractive_index + 0.1 * np.sin(comb_x_values_i*2*np.pi)
  absorption_coeffient_transoformed = absorption_coefficient * np.exp(-comb_x_values_i / 1.5e14)
  H_absorption_value = np.exp(-absorption_coeffient_transoformed * path_length)
  H_phase_value = np.exp(-1j * 2 * np.pi * comb_x_values_i * (refractive_index_transformed - 1) * path_length / speed_of_light)
  H_value = H_absorption_value * H_phase_value
  return H_value

def comb_y(cps3, comb_x_values_j):
  # Identify the basic independent variable points representing the entire wave, known as samples
  number_of_samples = int(cps3['time'] * cps3['sample_rate'])
  sample_set = np.zeros(number_of_samples) # Unit is 'number of samples,' representing total amount of points present in the grand train

  # Addresses pulses in the wave
  number_of_pulses_without_reference_to_samples = int(cps3['time'] * cps3['rep_rate'])
  amount_of_samples_coincident_with_pulses = int(cps3['pulse_duration'] * cps3['sample_rate']) # in just one pulse

  # Identify the time points (with units of seconds, not to be confused with sample points) at which pulses start
  pulse_drift_black_box = np.linspace(0,
                                      cps3['drift'] / cps3['rep_rate'],
                                      number_of_pulses_without_reference_to_samples) * np.exp(np.linspace(0,
                                                                                                          100 * cps3['drift'],
                                                                                                          number_of_pulses_without_reference_to_samples))
  pulse_times_noise_black_box = np.random.normal(loc = np.arange(number_of_pulses_without_reference_to_samples) / cps3['rep_rate'],
                                                 scale = cps3['jitter'] / cps3['rep_rate'],
                                                 size = number_of_pulses_without_reference_to_samples)

  # Synthesize to determine pulse time start points
  actual_pulse_time_start_points = np.add(pulse_times_noise_black_box,
                                          pulse_drift_black_box)

  # Wherever sample points are coincident with pulse points, set those sample values to one
  for actual_pulse_time_start_point in actual_pulse_time_start_points:
    starting_sample = int(actual_pulse_time_start_point * cps3['sample_rate'])
    if starting_sample + amount_of_samples_coincident_with_pulses < number_of_samples:
      sample_set[starting_sample:starting_sample + amount_of_samples_coincident_with_pulses] = 1

  # Add noise to all points of the sample train
  sample_set += cps3['noise'] * np.random.normal(size = number_of_samples)

  # Perform Fourier transform on the sample train to identify ampltidues of constituent frequencies
  fourier_amplitudes = np.fft.fft(sample_set)

  # Modify spectrum according to H parameter
  h_parameter = calculate_h(cps3, comb_x_values_j)
  final_amplitudes = fourier_amplitudes * h_parameter
  return np.abs(final_amplitudes)

def find_center(start_freq, first_harmon_width0):
  center = start_freq + (0.5 * first_harmon_width0)
  return center

def trim_data(final_x_axis0, final_y_axis0, horizontal_comb_shift0, width_of_each_comb0):
  lower_bound_first_harmonic = horizontal_comb_shift0 - (0.5 * width_of_each_comb0)
  upper_bound_first_harmonic = horizontal_comb_shift0 + (0.5 * width_of_each_comb0)

  new_x_axis = []
  new_y_axis = []

  for individual in range(len(final_x_axis0)):
    if final_x_axis0[individual] >= lower_bound_first_harmonic and final_x_axis0[individual] < upper_bound_first_harmonic:
      new_x_axis.append(final_x_axis0[individual])
      new_y_axis.append(final_y_axis0[individual])

  grand_update = []
  grand_update.append(new_x_axis)
  grand_update.append(new_y_axis)
  return grand_update

# Argparse architecture
parser = argparse.ArgumentParser()

# Add arguments
parser.add_argument('master_parameter', type = int)
parser.add_argument('thermal_parameter', type = int)
parser.add_argument('collected_ctr', type = int)
parser.add_argument('collected_width', type = int)
parser.add_argument('collected_no_teeth_per_wn', type = int)

# Parse arguments from command line
args = parser.parse_args()

# Add input
input_npy_file = f'/u/project/andreabertozzi/mfloridi/testing_suite/upstream/count_50_per/upstream_m{args.master_parameter}_t{args.thermal_parameter}.npy'
centers = [args.collected_ctr]
widths = [args.collected_width]
no_teeth_vs = [args.collected_no_teeth_per_wn]
output_path_sans_name = f'/u/project/andreabertozzi/mfloridi/testing_suite/downstream/count_50_per/teeth_per_wavenumber/m{args.master_parameter}_t{args.thermal_parameter}/'

ir_spectrum_unprocessed = np.load(input_npy_file)
frequencies = ir_spectrum_unprocessed[0]
divisor = ((ir_spectrum_unprocessed.shape[0]) - 1) / 10

# Pass combs through IR spectra
for widthpiece in widths:
  for no_teethpieces in no_teeth_vs:
    for centerpiece in centers:
      teeth_spacing = 1 / (no_teethpieces)
      name = f'm{args.master_parameter}_t{args.thermal_parameter}_c{centerpiece}_w{widthpiece}_tpwn{no_teethpieces}.csv'
      output_path = f'{output_path_sans_name}{name}'

      # Main parameters
      wavenumber_broadness = 3 * widthpiece
      horizontal_comb_shift = centerpiece
      noise_of_pulse = 0.00

      # Other parameters
      drift_comb = (args.master_parameter) * 2.5e-5                  # Jack set this parameter to 0.010
      jitter_comb = (args.master_parameter) * 5e-5
      refractive_index_comb = 000.0
      absorption_coefficient_comb = 0.0
      total_experiment_duration = 1e3

      # Apply parameters
      broadness_of_comb = wavenumber_broadness / 100
      comb_parameters = {'rep_rate': teeth_spacing,
                         'pulse_duration': 60e-3 * (1 / broadness_of_comb),
                         'time': total_experiment_duration,
                         'sample_rate': 100e0 * broadness_of_comb,
                         'noise': noise_of_pulse,
                         'jitter': jitter_comb,
                         'drift': drift_comb,
                         'n_0': refractive_index_comb,
                         'alpha_0': absorption_coefficient_comb}

      # Pass input through comb creation functions defined above
      comb_x_axis = comb_x(comb_parameters)
      comb_y_axis = comb_y(comb_parameters, comb_x_axis)
      final_x_axis = comb_x_axis + horizontal_comb_shift
      final_y_axis = comb_y_axis / (np.max(comb_y_axis))

      new_values = trim_data(final_x_axis, final_y_axis, centerpiece, widthpiece)

      sorted_indices = np.argsort(new_values[0])

      progress = 0
      for move in range(1, ir_spectrum_unprocessed.shape[0]):
        # Normalize current IR spectra
        transmittance_values = ir_spectrum_unprocessed[move] / (np.max(ir_spectrum_unprocessed[move]))

        # Interpolate IR spectra values and simulate interaction with comb
        ir_spectrum_interpolated_values = np.interp(x = new_values[0], xp = frequencies, fp = transmittance_values)
        exiting_comb = ir_spectrum_interpolated_values * new_values[1]

        if (progress == 0):
          chart = []
          column_names = []
          for ex in range(len(sorted_indices)):
            name = f'comb_point_{ex}'
            column_names.append(name)
          column_names.extend(['master_noise_parameter', 'thermal_noise_parameter', 'total_teeth', 'teeth_per_wavenumber', 'width', 'center', 'name'])
          chart.append(column_names)

        updated_y = []
        for finality in sorted_indices:
          updated_y.append(exiting_comb[finality])
        updated_y.append(args.master_parameter)
        updated_y.append(args.thermal_parameter)
        updated_y.append(no_teethpieces * widthpiece)
        updated_y.append(no_teethpieces)
        updated_y.append(widthpiece)
        updated_y.append(centerpiece)
        updated_y.append(progress // divisor)

        chart.append(updated_y)
        progress = progress + 1

      # Write output to csv
      with open(output_path, mode = 'w', newline = '') as file:
        writer = csv.writer(file)

        for row in chart:
          writer.writerow(row)
