from autode.transition_states import locate_tss
from autode import molecule
from autode import reaction
from autode.bond_rearrangement import BondRearrangement

# h + h > h2 dissociation
h_product_1 = molecule.Product(name= 'H',xyzs=[['H', 0.0, 0.0, 0.0]])
h_product_2 = molecule.Product(name= 'H',xyzs=[['H', 1.0, 0.0, 0.0]])
hh_reactant = molecule.Reactant(name='H2',xyzs=[['H', 0.0, 0.0, 0.0], ['H', 0.7, 0.0, 0.0]])
dissoc_reaction = reaction.Reaction(name='dissoc',mol1=h_product_1, mol2=h_product_2, mol3=hh_reactant)
dissoc_reactant, dissoc_product = locate_tss.get_reactant_and_product_complexes(dissoc_reaction)
dissoc_rearrangs = locate_tss.get_bond_rearrangs(dissoc_reactant, dissoc_product)

# h2 + h > h + h2 substitution
h_reactant = molecule.Reactant(name='H',xyzs=[['H', 0.0, 0.0, 0.0]])
hh_product = molecule.Product(name='H2',xyzs=[['H', 0.7, 0.0, 0.0], ['H', 1.4, 0.0, 0.0]])
subs_reaction = reaction.Reaction(name='subs',mol1=h_reactant, mol2=hh_reactant, mol3=hh_product, mol4=h_product_2)
subs_reactant, subs_product = locate_tss.get_reactant_and_product_complexes(subs_reaction)
subs_rearrangs = locate_tss.get_bond_rearrangs(subs_reactant, subs_product)

# ch2fch2+ > +chfch3 rearrangement
alkyl_reactant = molecule.Reactant(smiles='[CH2+]CF')
alkyl_product = molecule.Product(smiles='C[CH+]F')
rearang_reaction = reaction.Reaction(name='rearang', mol1=alkyl_reactant, mol2=alkyl_product)
rearrang_reactant, rearrang_product = locate_tss.get_reactant_and_product_complexes(rearang_reaction)
rearrang_rearrangs = locate_tss.get_bond_rearrangs(rearrang_reactant, rearrang_product)

def test_reac_and_prod_complexes():

    assert type(dissoc_reactant) == molecule.Reactant
    assert type(dissoc_product) == molecule.Molecule
    assert len(dissoc_reactant.xyzs) == 2
    assert len(dissoc_product.xyzs) == 2

    assert type(subs_reactant) == molecule.Molecule
    assert type(subs_product) == molecule.Molecule
    assert len(subs_reactant.xyzs) == 3
    assert len(subs_product.xyzs) == 3

    assert type(rearrang_reactant) == molecule.Reactant
    assert type(rearrang_product) == molecule.Product
    assert len(rearrang_reactant.xyzs) == 7
    assert len(rearrang_product.xyzs) == 7

def test_get_bond_rearrangs():
    
    assert len(dissoc_rearrangs) == 1
    assert type(dissoc_rearrangs[0]) == BondRearrangement
    assert dissoc_rearrangs[0].all == [(0,1)]

    assert len(subs_rearrangs) == 1
    assert type(subs_rearrangs[0]) == BondRearrangement
    assert subs_rearrangs[0].all == [(0,1), (1,2)]

    assert len(rearrang_rearrangs) == 1
    assert type(rearrang_rearrangs[0]) == BondRearrangement
    assert rearrang_rearrangs[0].all == [(0,5), (1,5)]


def test_add_bond_rearrangement():
    #rearrangment doesn't get product, shouldn't be added
    bond_rearrangs = locate_tss.add_bond_rearrangment([], subs_reactant, subs_product, [(0,1)], [])
    assert bond_rearrangs == []


def test_rearranged_graph():
    rearranged_graph = locate_tss.generate_rearranged_graph(subs_reactant.graph, [(0,1)], [(1,2)])
    assert locate_tss.is_isomorphic(rearranged_graph, subs_product.graph)


def test_get_funcs_and_params():
    dissoc_f_and_p = locate_tss.get_ts_guess_funcs_and_params(dissoc_reaction, dissoc_reactant, dissoc_rearrangs[0])
    assert type(dissoc_f_and_p) == list
    assert len(dissoc_f_and_p) == 4
    assert dissoc_f_and_p[0][0] == locate_tss.get_template_ts_guess
    assert type(dissoc_f_and_p[1][1][0]) == molecule.Reactant
    assert dissoc_f_and_p[1][1][1] == (0,1)
    assert dissoc_f_and_p[1][1][3] == 'H2--H+H_0-1_ll1d'
    assert dissoc_f_and_p[3][1][4] == locate_tss.Dissociation

    subs_f_and_p = locate_tss.get_ts_guess_funcs_and_params(subs_reaction, subs_reactant, subs_rearrangs[0])
    assert type(subs_f_and_p) == list
    assert len(subs_f_and_p) == 7
    assert subs_f_and_p[3][1][4] == locate_tss.Substitution


def test_strip_equivalent_rearrangements():
    #5 and 6 should be equivalent Hs
    possible_bond_rearrangs = [BondRearrangement([(0,5)], [(1,5)]), BondRearrangement([(0,6)], [(1,6)])]
    unique_rearrangs = locate_tss.strip_equivalent_bond_rearrangs(rearrang_reactant, possible_bond_rearrangs)
    assert len(unique_rearrangs) == 1


def test_locate_tss():
    ts = locate_tss.find_tss(rearrang_rearrangs)