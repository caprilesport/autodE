from .config import Config
from .log import logger
from rdkit.Chem import AllChem
from rdkit import Chem
import rdkit.Chem.Descriptors
from . import mol_graphs
from .constants import Constants
from .conformers import generate_unique_rdkit_confs
from .bond_lengths import get_xyz_bond_list
from .bond_lengths import get_bond_list_from_rdkit_bonds
from .geom import calc_distance_matrix
from .conformers import gen_rdkit_conf_xyzs
from .conformers import Conformer
from .conformers import rdkit_conformer_geometries_are_resonable
from .conf_gen import gen_simanl_conf_xyzs
from .opt import get_opt_xyzs_energy
from .single_point import get_single_point_energy


def calc_multiplicity(n_radical_electrons):
    """
    Calculate the spin multiplicity 2S + 1 where S is the number of unpaired electrons
    :return:
    """

    try:
        assert n_radical_electrons <= 1
    except AssertionError:
        logger.critical('Diradicals are not yet supported')
        exit()
    return 2 if n_radical_electrons == 1 else 1


class Molecule(object):

    def get_active_mol_graph(self, active_bonds):
        logger.info('Getting molecular graph with active edges')
        active_graph = self.graph.copy()

        for bond in active_bonds:
            has_edge = False
            for edge in active_graph.edges():
                if edge == bond or edge == tuple(reversed(bond)):
                    has_edge = True
                    active_graph.edges[edge[0], edge[1]]['active'] = True

            if not has_edge:
                active_graph.add_edge(*bond, active=True)

        return active_graph

    def check_rdkit_graph_agreement(self):
        try:
            assert self.n_bonds == self.graph.number_of_edges()
        except AssertionError:
            logger.error('Number of rdkit bonds doesn\'t match the the molecular graph')
            exit()

    def generate_conformers(self, n_rdkit_confs=300):

        self.conformers = []

        if self.rdkit_conf_gen_is_fine:
            logger.info('Generating Molecule conformer xyz lists from rdkit mol object')
            unique_conf_ids = generate_unique_rdkit_confs(self.mol_obj, n_rdkit_confs)
            logger.info('Generated {} unique conformers with RDKit ETKDG'.format(len(unique_conf_ids)))
            conf_xyzs = gen_rdkit_conf_xyzs(self, conf_ids=unique_conf_ids)

        else:
            bond_list = get_bond_list_from_rdkit_bonds(rdkit_bonds_obj=self.mol_obj.GetBonds())
            conf_xyzs = gen_simanl_conf_xyzs(name=self.name, init_xyzs=self.xyzs, bond_list=bond_list,
                                             charge=self.charge)

        for i in range(len(conf_xyzs)):
            self.conformers.append(Conformer(name=self.name + '_conf' + str(i), xyzs=conf_xyzs[i],
                                             solvent=self.solvent, charge=self.charge, mult=self.mult))

        self.n_conformers = len(self.conformers)

    def strip_non_unique_confs(self, energy_threshold_kj=1):
        logger.info('Stripping conformers with energy ∆E < 1 kJ mol-1 to others')
        d_e = energy_threshold_kj / Constants.ha2kJmol                             # conformer.energy is in Hartrees
        unique_conformers = [self.conformers[0]]                                   # The first conformer must be unique

        for i in range(1, self.n_conformers):
            unique = True
            for j in range(len(unique_conformers)):
                if self.conformers[i].energy - d_e < self.conformers[j].energy < self.conformers[i].energy + d_e:
                    unique = False
                    break
            if unique:
                unique_conformers.append(self.conformers[i])

        logger.info('Stripped {} conformers from a total of {}'.format(self.n_conformers - len(unique_conformers),
                                                                       self.n_conformers))
        self.conformers = unique_conformers
        self.n_conformers = len(self.conformers)

    def optimise_conformers_xtb(self):
        logger.info('Optimising all conformers with xtb')
        [self.conformers[i].xtb_optimise() for i in range(len(self.conformers))]
        logger.info('XTB conformer optimisation done')

    def optimise_conformers_orca(self):
        logger.info('Optimising all conformers with ORCA')
        [self.conformers[i].orca_optimise() for i in range(len(self.conformers))]
        logger.info('ORCA conformer optimisation done')

    def find_lowest_energy_conformer(self):
        """
        For a molecule object find the lowest in energy and set it as the mol.xyzs and mol.energy
        :return:
        """
        if self.conformers is None:
            logger.critical('Have no conformers')
            exit()
        lowest_energy = min([conf.energy for conf in self.conformers])
        for conformer in self.conformers:
            if conformer.energy == lowest_energy:
                self.energy = conformer.energy
                self.xyzs = conformer.xyzs
                self.distance_matrix = calc_distance_matrix(self.xyzs)
                self.graph = mol_graphs.make_graph(self.xyzs, self.n_atoms)
                break
        logger.info('Set lowest energy conformer energy & geometry as mol.energy & mol.xyzs')

    def optimise(self):
        self.xyzs, self.energy = get_opt_xyzs_energy(self, keywords=Config.opt_keywords, n_cores=Config.n_cores)

    def single_point(self):
        self.energy = get_single_point_energy(self, keywords=Config.sp_keywords, n_cores=Config.n_cores)

    def init_smiles(self, name, smiles):

        try:
            self.mol_obj = Chem.MolFromSmiles(smiles)
            self.mol_obj = Chem.AddHs(self.mol_obj)
        except RuntimeError:
            logger.critical('Could not generate an rdkit mol object for {}'.format(name))
            exit()

        self.n_atoms = self.mol_obj.GetNumAtoms()
        self.n_bonds = len(self.mol_obj.GetBonds())
        self.charge = Chem.GetFormalCharge(self.mol_obj)
        n_radical_electrons = rdkit.Chem.Descriptors.NumRadicalElectrons(self.mol_obj)
        self.mult = calc_multiplicity(n_radical_electrons)

        AllChem.EmbedMultipleConfs(self.mol_obj, numConfs=1, params=AllChem.ETKDG())
        self.xyzs = gen_rdkit_conf_xyzs(self, conf_ids=[0])[0]

        if not rdkit_conformer_geometries_are_resonable(conf_xyzs=[self.xyzs]):
            logger.info('RDKit conformer was not reasonable')
            self.rdkit_conf_gen_is_fine = False
            bond_list = get_bond_list_from_rdkit_bonds(rdkit_bonds_obj=self.mol_obj.GetBonds())
            self.xyzs = gen_simanl_conf_xyzs(name=self.name, init_xyzs=self.xyzs, bond_list=bond_list,
                                             charge=self.charge, n_simanls=1)[0]
            self.graph = mol_graphs.make_graph(self.xyzs, self.n_atoms)
            self.n_bonds = self.graph.number_of_edges()

        else:
            self.graph = mol_graphs.make_graph(self.xyzs, self.n_atoms)
            self.check_rdkit_graph_agreement()

        self.distance_matrix = calc_distance_matrix(self.xyzs)

    def init_xyzs(self, xyzs):
        self.n_atoms = len(xyzs)
        self.n_bonds = len(get_xyz_bond_list(xyzs))
        self.graph = mol_graphs.make_graph(self.xyzs, self.n_atoms)
        self.distance_matrix = calc_distance_matrix(xyzs)

    def __init__(self, name='molecule', smiles=None, xyzs=None, solvent=None, charge=0, mult=1):
        """
        Initialise a Molecule object.
        Will generate xyz lists of all the conformers found by RDKit within the number
        of conformers searched (n_confs)
        :param name: (str) Name of the molecule
        :param smiles: (str) Standard SMILES string. e.g. generated by Chemdraw
        :param solvent: (str) Solvent that the molecule is immersed in. Will be used in optimise() and single_point()
        :param charge: (int) charge on the molecule
        :param mult: (int) spin multiplicity on the molecule
        """
        logger.info('Generating a Molecule object for {}'.format(name))

        self.name = name
        self.smiles = smiles
        self.solvent = solvent
        self.charge = charge
        self.mult = mult
        self.xyzs = xyzs
        self.mol_obj = None
        self.energy = None
        self.n_atoms = None
        self.n_bonds = None
        self.conformers = None
        self.n_conformers = None
        self.rdkit_conf_gen_is_fine = True
        self.graph = None
        self.distance_matrix = None

        if smiles:
            self.init_smiles(name, smiles)

        if xyzs:
            self.init_xyzs(xyzs)


class Reactant(Molecule):
    pass


class Product(Molecule):
    pass