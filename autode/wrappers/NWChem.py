from autode.config import Config
from autode.log import logger
from autode.constants import Constants
from autode.wrappers.base import ElectronicStructureMethod
from autode.wrappers.base import req_methods
from autode.input_output import xyzs2xyzfile
import numpy as np
import os

smd_solvents = ['h2o', 'water', 'acetacid', 'acetone', 'acetntrl', 'acetphen', 'aniline', 'anisole', 'benzaldh', 'benzene', 'benzntrl', 'benzylcl', 'brisobut',
                'brbenzen', 'brethane', 'bromform', 'broctane', 'brpentan', 'brpropa2', 'brpropan', 'butanal', 'butacid', 'butanol', 'butanol2', 'butanone',
                'butantrl', 'butile', 'nba', 'nbutbenz', 'sbutbenz', 'tbutbenz', 'cs2', 'carbntet', 'clbenzen', 'secbutcl', 'chcl3', 'clhexane', 'clpentan',
                'clpropan', 'ocltolue', 'm-cresol', 'o-cresol', 'cychexan', 'cychexon', 'cycpentn', 'cycpntol', 'cycpnton', 'declncis', 'declntra', 'declnmix',
                'decane', 'decanol', 'edb12', 'dibrmetn', 'butyleth', 'odiclbnz', 'edc12', 'c12dce', 't12dce', 'dcm', 'ether', 'et2s', 'dietamin', 'mi', 'dipe',
                'dmds', 'dmso', 'dma', 'cisdmchx', 'dmf', 'dmepen24', 'dmepyr24', 'dmepyr26', 'dioxane', 'phoph', 'dproamin', 'dodecan', 'meg', 'etsh', 'ethanol',
                'etoac', 'etome', 'eb', 'phenetol', 'c6h5f', 'foctane', 'formamid', 'formacid', 'heptane', 'heptanol', 'heptnon2', 'heptnon4', 'hexadecn',
                'hexane', 'hexnacid', 'hexanol', 'hexanon2', 'hexene', 'hexyne', 'c6h5i', 'iobutane', 'c2h5i', 'iohexdec', 'ch3i', 'iopentan', 'iopropan',
                'cumene', 'p-cymene', 'mesityln', 'methanol', 'egme', 'meacetat', 'mebnzate', 'mebutate', 'meformat', 'mibk', 'mepropyl', 'isobutol', 'terbutol',
                'nmeaniln', 'mecychex', 'nmfmixtr', 'isohexan', 'mepyrid2', 'mepyrid3', 'mepyrid4', 'c6h5no2', 'c2h5no2', 'ch3no2', 'ntrprop1', 'ntrprop2',
                'ontrtolu', 'nonane', 'nonanol', 'nonanone', 'octane', 'octanol', 'octanon2', 'pentdecn', 'pentanal', 'npentane', 'pentacid', 'pentanol', 'pentnon2',
                'pentnon3', 'pentene', 'e2penten', 'pentacet', 'pentamin', 'pfb', 'benzalcl', 'propanal', 'propacid', 'propanol', 'propnol2', 'propntrl', 'propenol',
                'propacet', 'propamin', 'pyridine', 'c2cl4', 'thf', 'sulfolan', 'tetralin', 'thiophen', 'phsh', 'toluene', 'tbp', 'tca111', 'tca112', 'tce', 'et3n',
                'tfe222', 'tmben124', 'isoctane', 'undecane', 'm-xylene', 'o-xylene', 'p-xylene', 'xylenemx']

NWChem = ElectronicStructureMethod(name='nwchem', path=Config.NWChem.path,
                                   aval_solvents=[solv.lower()
                                                  for solv in smd_solvents],
                                   scan_keywords=Config.NWChem.scan_keywords,
                                   conf_opt_keywords=Config.NWChem.conf_opt_keywords,
                                   opt_keywords=Config.NWChem.opt_keywords,
                                   opt_ts_keywords=Config.NWChem.opt_ts_keywords,
                                   hess_keywords=Config.NWChem.hess_keywords,
                                   sp_keywords=Config.NWChem.sp_keywords,
                                   mpirun=True)

NWChem.__name__ = 'NWChem'


def generate_input(calc):
    calc.input_filename = calc.name + '_nwchem.nw'
    calc.output_filename = calc.name + '_nwchem.out'
    keywords = calc.keywords.copy()

    new_keywords = []
    scf_block = False
    for keyword in keywords:
        if 'opt' in keyword.lower() and calc.n_atoms == 1:
            logger.warning('Cannot do an optimisation for a single atom')
            old_key = keyword.split()
            new_keyword = ' '
            for word in old_key:
                if 'opt' in word:
                    new_keyword += 'energy '
                else:
                    new_keyword += word + ' '
            new_keywords.append(new_keyword)
        elif keyword.lower().startswith('dft'):
            lines = keyword.split('\n')
            lines.insert(1, f'  mult {calc.mult}')
            new_keyword = '\n'.join(lines)
            new_keywords.append(new_keyword)
        elif keyword.lower().startswith('scf'):
            scf_block = True
            lines = keyword.split('\n')
            lines.insert(1, f'  nopen {calc.mult - 1}')
            new_keyword = '\n'.join(lines)
            new_keywords.append(new_keyword)
        elif any(string in keyword.lower() for string in ['ccsd', 'mp2']) and not scf_block:
            new_keywords.append(f'scf\n  nopen {calc.mult - 1}\nend')
            new_keywords.append(keyword)
        else:
            new_keywords.append(keyword)
    keywords = new_keywords

    with open(calc.input_filename, 'w') as inp_file:

        print(f'start {calc.name}_nwchem\necho', file=inp_file)

        if calc.solvent:
            print(
                f'cosmo\n do_cosmo_smd true\n solvent {calc.solvent}\nend', file=inp_file)

        print('geometry', end=' ', file=inp_file)
        if calc.distance_constraints or calc.cartesian_constraints:
            print('noautoz', file=inp_file)
        else:
            print('', file=inp_file)
        [print('  {:<3} {:^12.8f} {:^12.8f} {:^12.8f}'.format(
            *line), file=inp_file) for line in calc.xyzs]
        if calc.bond_ids_to_add or calc.distance_constraints:
            print('  zcoord', file=inp_file)
            if calc.bond_ids_to_add:
                try:
                    [print('    bond', bond_ids[0] + 1, bond_ids[1] + 1,
                           file=inp_file) for bond_ids in calc.bond_ids_to_add]
                except (IndexError, TypeError):
                    logger.error('Could not add scanned bond')
            if calc.distance_constraints:
                [print('    bond', atom_ids[0] + 1, atom_ids[1] + 1, file=inp_file)
                 for atom_ids in calc.distance_constraints.keys()]
            print('  end', file=inp_file)
        print('end', file=inp_file)

        print(f'charge {calc.charge}', file=inp_file)

        if calc.distance_constraints or calc.cartesian_constraints:
            force_constant = 10
            if calc.constraints_already_met:
                force_constant += 90
            print('constraints', file=inp_file)
            if calc.distance_constraints:
                for atom_ids in calc.distance_constraints.keys():  # NWChem counts from 1 so increment atom ids by 1
                    print(f'  spring bond {atom_ids[0] + 1} {atom_ids[1] + 1} {force_constant} {np.round(calc.distance_constraints[atom_ids], 3)}' + str(
                        atom_ids[0] + 1), file=inp_file)

            if calc.cartesian_constraints:
                constrained_atoms = [i + 1 for i in calc.cartesian_constraints]
                list_of_ranges = []
                used_atoms = []
                for atom in constrained_atoms:
                    rang = []
                    if atom not in used_atoms:
                        while atom in constrained_atoms:
                            used_atoms.append(atom)
                            rang.append(atom)
                            atom += 1
                        if len(rang) in (1, 2):
                            list_of_ranges += rang
                        else:
                            range_string = str(rang[0]) + ':' + str(rang[-1])
                            list_of_ranges.append(range_string)
                print('  fix atom', end=' ', file=inp_file)
                print(*list_of_ranges, sep=' ', file=inp_file)
            print('end', file=inp_file)

        print(f'memory {Config.max_core} mb', file=inp_file)

        print(*keywords, sep='\n', file=inp_file)

    return None


def calculation_terminated_normally(calc):

    for n_line, line in enumerate(calc.rev_output_file_lines):
        if any(substring in line for substring in['CITATION', 'Failed to converge in maximum number of steps or available time']):
            logger.info('NWChem terminated normally')
            return True
        if n_line > 500:
            return False


def get_energy(calc):

    for line in calc.rev_output_file_lines:
        if any(string in line for string in ['Total DFT energy', 'Total SCF energy']):
            return float(line.split()[4])
        if any(string in line for string in ['Total CCSD energy', 'Total CCSD(T) energy', 'Total SCS-MP2 energy', 'Total MP2 energy', 'Total RI-MP2 energy']):
            return float(line.split()[3])


def optimisation_converged(calc):

    for line in calc.rev_output_file_lines:
        if 'Optimization converged' in line:
            return True

    return False


def optimisation_nearly_converged(calc):

    for j, line in enumerate(calc.rev_output_file_lines):
        if '@' in line:
            if 'ok' in calc.rev_output_file_lines[j-1]:
                return True

    return False


def get_imag_freqs(calc):

    imag_freqs = None
    normal_mode_section = False

    for line in calc.output_file_lines:
        if 'Projected Frequencies' in line:
            normal_mode_section = True
            imag_freqs = []

        if '------------------------------' in line:
            normal_mode_section = False

        if normal_mode_section and 'P.Frequency' in line:
            freqs = [float(line.split()[i])
                     for i in range(1, len(line.split()))]
            for freq in freqs:
                if freq < 0:
                    imag_freqs.append(freq)

    logger.info(f'Found imaginary freqs {imag_freqs}')
    return imag_freqs


def get_normal_mode_displacements(calc, mode_number):

    # mode numbers start at 1, not 6
    mode_number -= 5
    normal_mode_section, displacements = False, []

    for j, line in enumerate(calc.output_file_lines):
        if 'Projected Frequencies' in line:
            normal_mode_section = True
            displacements = []

        if '------------------------------' in line:
            normal_mode_section = False

        if normal_mode_section:
            if len(line.split()) == 6:
                mode_numbers = [int(val) for val in line.split()]
                if mode_number in mode_numbers:
                    col = [i for i in range(
                        len(mode_numbers)) if mode_number == mode_numbers[i]][0] + 1
                    displacements = [float(disp_line.split()[
                        col]) for disp_line in calc.output_file_lines[j + 4:j + 3 * calc.n_atoms + 4]]

    displacements_xyz = [displacements[i:i + 3]
                         for i in range(0, len(displacements), 3)]
    if len(displacements_xyz) != calc.n_atoms:
        logger.error(
            'Something went wrong getting the displacements n != n_atoms')
        return None

    return displacements_xyz


def get_final_xyzs(calc):

    xyzs_section = False
    xyzs = []

    for line in calc.output_file_lines:
        if 'Output coordinates in angstroms' in line:
            xyzs_section = True
            xyzs = []

        if 'Atomic Mass' in line:
            xyzs_section = False

        if xyzs_section and len(line.split()) == 6:
            if line.split()[0].isdigit():
                _, atom_label, _, x, y, z = line.split()
                xyzs.append([atom_label, float(x), float(y), float(z)])

    xyz_filename = f'{calc.name}_nwchem.xyz'
    xyzs2xyzfile(xyzs, xyz_filename)

    return xyzs


# Bind all the required functions to the class definition
[setattr(NWChem, method, globals()[method]) for method in req_methods]