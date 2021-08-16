"""
Base Topological Encoder Classes
"""
from abc import abstractmethod, ABCMeta
from typing import TypeVar, Tuple, Dict, List, Generic, Optional, Type, Any
from qiskit import QuantumRegister, QuantumCircuit, ClassicalRegister
from qiskit.circuit.quantumregister import Qubit

TQubit = TypeVar("TQubit")


class LatticeError(Exception):
    """
    Lattice Inconsistency Errors
    """


class _Stabilizer(metaclass=ABCMeta):
    """
    A blueprint for stabilizer classes, such as plaquettes for surface codes.
    """

    def __init__(self, circ: QuantumCircuit, qubit_indices: List[List[Qubit]]):
        self.circ = circ
        self.qubit_indices = qubit_indices

    @abstractmethod
    def entangle(self):
        """
        Entangles qubits to form a plaquette
        """


class _TopologicalLattice(Generic[TQubit], metaclass=ABCMeta):
    """
    This abstract class contains a blueprint for lattice construction.
    """

    def __init__(
        self, params: Dict[str, float], name: str, circ: QuantumCircuit,
    ):
        """
        Initializes this Topological Lattice class.

        Args:
            params (Dict[str,int]):
                Contains params such as d, where d is the number of
                physical "data" qubits lining a row or column of the lattice.
            name (str):
                Useful when combining multiple TopologicalQubits together.
                Prepended to all registers.
            circ (QuantumCircuit):
                QuantumCircuit on top of which the topological qubit is built.
                This is often shared amongst multiple TQubits.
        """

        self.name = name
        self.circ = circ
        self.params: Dict[str, float] = params
        self._params_validate_and_generate()

        self.qregisters: Dict[str, QuantumRegister] = {}  # quantum
        self.cregisters: Dict[str, ClassicalRegister] = {}  # classical
        self._gen_registers()

        assert "data" in self.qregisters, "There should be a data qubits register."

        # add registerse to circ
        registers = list(self.qregisters.values()) + list(self.cregisters.values())
        self.circ.add_register(*registers)

        self.qubit_indices, self.stabilizers = self._gen_qubit_indices_and_stabilizers()

    @abstractmethod
    def _params_validate_and_generate(self) -> None:
        """
        Validate and generate params.

        E.g.
        self.params["num_syn"] = params["d"] - 1
        """

    @abstractmethod
    def _gen_registers(self) -> None:
        """
        Implement this method to create quantum and classical registers.

        E.g.
        qregisters["data"] = QuantumRegister(params["num_data"], name=name + "_data")
        """

    @abstractmethod
    def _gen_qubit_indices_and_stabilizers(
        self,
    ) -> Tuple[List[List[Qubit]], List[Type[Any]]]:
        """
        Generates lattice blueprint for rotated surface code lattice with our
        chosen layout and numbering.

        Returns:
            qubit_indices (List[List[Qubit]]):
                List of lists of Qubits that comprise each plaquette.

            stabilizers (List[_Stabilizer]):
                List of stabilizers for each plaquette.
        """

    def entangle(
        self,
        qubit_indices: Optional[List[List[Qubit]]] = None,
        stabilizers: Optional[List[Type[_Stabilizer]]] = None,
    ) -> None:
        """
        Entangles plaquettes as per the instruction set stored in qubit_indices
        and stabilizers and generated by _gen_qubit_indices_and_stabilizers

        Args:
            qubit_indices (Optional[List[List[Qubit]]]):
                List of lists of Qubits that comprise each plaquette.
                This is optional, and will be used instead of self.qubit_indices if provided.
            stabilizers (Optional[List[_Stabilizer]]):
                List of stabilizers for each plaquette.
                This is optional, and will be used instead of self.stabilizers if provided.
        """
        qubit_indices = qubit_indices if qubit_indices else self.qubit_indices
        stabilizers = stabilizers if stabilizers else self.stabilizers

        for i, stabilizer_cls in enumerate(stabilizers):
            stabilizer = stabilizer_cls(self.circ, qubit_indices[i])
            stabilizer.entangle()
            self.circ.barrier()

    @abstractmethod
    def reset_x(self) -> None:
        """
        Initialize/reset to a logical |x+> state.
        """

    @abstractmethod
    def reset_z(self) -> None:
        """
        Initialize/reset to a logical |z+> state.
        """

    @abstractmethod
    def x(self) -> None:
        """
        Logical X operator on the topological qubit.
        """

    @abstractmethod
    def z(self) -> None:
        """
        Logical Z operator on the topological qubit.
        """

    @abstractmethod
    def x_c_if(self, classical: ClassicalRegister, val: int) -> None:
        """
        Classically conditioned logical X operator on the topological qubit.
        """

    @abstractmethod
    def z_c_if(self, classical: ClassicalRegister, val: int) -> None:
        """
        Classically conditioned logical Z operator on the topological qubit.
        """

    @abstractmethod
    def cx(self, control: Optional[Qubit] = None, target: Optional[Qubit] = None):
        """
        Logical CX Gate

        Args:
            control (Optional[Qubit]): If provided, then this gate will implement
                a logical x gate on this tqubit conditioned on source

            target (Optional[Qubit]): If provided, then this gate will implement
                a logical x gate on target conditioned on this tqubit
        """

    @abstractmethod
    def readout_x(self, readout_creg: Optional[ClassicalRegister] = None) -> None:
        """
        Convenience method to read-out the logical-X projection.
        """

    @abstractmethod
    def readout_z(self, readout_creg: Optional[ClassicalRegister] = None) -> None:
        """
        Convenience method to read-out the logical-Z projection.
        """

    @abstractmethod
    def lattice_readout_x(self) -> None:
        """
        Readout all data qubits that constitute the lattice.
        This readout can be used to extract a final round of stabilizer measurments,
        as well as a logical X readout.
        """

    @abstractmethod
    def lattice_readout_z(self) -> None:
        """
        Readout all data qubits that constitute the lattice.
        This readout can be used to extract a final round of stabilizer measurments,
        as well as a logical Z readout.
        """

    @abstractmethod
    def parse_readout(
        self, readout_string: str, readout_type: Optional[str] = None
    ) -> Tuple[int, Dict[str, List[TQubit]]]:
        """
        Helper method to turn a result string (e.g. 1 10100000 10010000) into an
        appropriate logical readout value and XOR-ed syndrome locations
        according to our grid coordinate convention.

        The implementation varies with different topological qubits,
        but here's an example from the rotated surface code:

        Args:
            readout_string (str):
                Readout of the form "0 00000000 00000000" (logical_readout syndrome_1 syndrome_0)
                or of the form "000000000 00000000 00000000" (lattice_readout syndrome_1 syndrome_0)
        Returns:
            logical_readout (int):
                logical readout value
            syndromes (Dict[str, List[TQubit]]]):
                key: syndrome type
                value: (time, row, col) of parsed syndrome hits (changes between consecutive rounds)
        """


class TopologicalQubit(Generic[TQubit], metaclass=ABCMeta):
    """
    A single topological code logical qubit.
    This stores a QuantumCircuit object onto which the topological circuit is built.
    This abstract class contains a list of abstract methods
    that should be implemented by subclasses.
    """

    @property
    @abstractmethod
    def lattice_type(self):
        """
        Subclass of _TopologicalLattice
        """

    def __init__(
        self, params: Dict[str, int], name: str, circ: Optional[QuantumCircuit] = None
    ) -> None:
        """
        Initializes this Topological Qubit class.

        Args:
            params (Dict[str,int]):
                Contains params such as d, where d is the number of
                physical "data" qubits lining a row or column of the lattice.
            name (str):
                Useful when combining multiple TopologicalQubits together.
                Prepended to all registers.
            circ (Optional[QuantumCircuit]):
                QuantumCircuit on top of which the topological qubit is built.
                This is often shared amongst multiple TQubits.
                If none is provided, then a new QuantumCircuit is initialized and stored.

        """
        # == None is necessary, as `not QuantumCircuit()` is True
        circ = QuantumCircuit() if circ is None else circ

        self.lattice = self.lattice_type(params, name, circ)
        self.name = name
        self.circ = circ

    def draw(self, **kwargs) -> None:
        """
        Convenience method to draw quantum circuit.
        """
        return self.circ.draw(**kwargs)

    def __str__(self) -> str:
        return self.circ.__str__()

    @abstractmethod
    def stabilize(self) -> None:
        """
        Run a single round of stabilization (entangle and measure).
        """

    def id(self) -> None:
        """
        Inserts an identity on the data and syndrome qubits.
        This allows us to create an isolated noise model by inserting errors only on identity gates.
        """
        for register in self.lattice.qregisters.values():
            self.circ.id(register)
        self.circ.barrier()

    def id_data(self) -> None:
        """
        Inserts an identity on the data qubits only.
        This allows us to create an isolated noise model by inserting errors only on identity gates.
        """
        self.circ.id(self.lattice.qregisters["data"])
        self.circ.barrier()

    def reset_x(self) -> None:
        """
        Initialize/reset to a logical |x+> state.
        """
        self.lattice.reset_x()

    def reset_z(self) -> None:
        """
        Initialize/reset to a logical |z+> state.
        """
        self.lattice.reset_z()

    def x(self) -> None:
        """
        Logical X operator on the topological qubit.
        """
        self.lattice.x()

    def z(self) -> None:
        """
        Logical Z operator on the topological qubit.
        """
        self.lattice.z()

    def x_c_if(self, classical: ClassicalRegister, val: int) -> None:
        """
        Classical conditioned logical X operator on the topological qubit.
        """
        self.lattice.x_c_if(classical, val)

    def z_c_if(self, classical: ClassicalRegister, val: int) -> None:
        """
        Classical conditioned logical Z operator on the topological qubit.
        """
        self.lattice.z_c_if(classical, val)

    def cx(self, control: Optional[Qubit] = None, target: Optional[Qubit] = None):
        """
        Logical CX Gate

        Args:
            control (Optional[Qubit]): If provided, then this gate will implement
                a logical x gate on this tqubit conditioned on source

            target (Optional[Qubit]): If provided, then this gate will implement
                a logical x gate on target conditioned on this tqubit

        Additional Information:
            Exactly one of control or target must be provided.
        """
        if not (bool(control) ^ bool(target)):
            raise ValueError("Please specify exactly one of source or target")
        self.lattice.cx(control, target)

    def readout_x(self, readout_creg: Optional[ClassicalRegister] = None) -> None:
        """
        Convenience method to read-out the logical-X projection.
        """
        self.lattice.readout_x(readout_creg=readout_creg)

    def readout_z(self, readout_creg: Optional[ClassicalRegister] = None) -> None:
        """
        Convenience method to read-out the logical-Z projection.
        """
        self.lattice.readout_z(readout_creg=readout_creg)

    def lattice_readout_x(self) -> None:
        """
        Readout all data qubits that constitute the lattice.
        This readout can be used to extract a final round of X stabilizer measurments,
        as well as a logical X readout.
        """
        self.lattice.lattice_readout_x()

    def lattice_readout_z(self) -> None:
        """
        Readout all data qubits that constitute the lattice.
        This readout can be used to extract a final round of Z stabilizer measurments,
        as well as a logical Z readout.
        """
        self.lattice.lattice_readout_z()

    def parse_readout(
        self, readout_string: str, readout_type: Optional[str] = None
    ) -> Tuple[int, Dict[str, List[TQubit]]]:
        """
        Wrapper on helper method to turn a result string (e.g. 1 10100000 10010000) into an
        appropriate logical readout value and XOR-ed syndrome locations
        according to our grid coordinate convention.
        """
        return self.lattice.parse_readout(readout_string, readout_type)
