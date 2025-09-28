namespace QuantumResEstVS {
    open Microsoft.Quantum.Intrinsic;
    open Microsoft.Quantum.Canon;

    // ---- Edit these constants to change experiment size ----
    internal function BitWidth() : Int { return 128; }
    internal function Reps()    : Int { return 4;   }
    // --------------------------------------------------------

    // Toy kernel:
    //  1) Put qubits in |+>
    //  2) Entangle with a CNOT chain
    //  3) Apply some non-Clifford T gates (gives nonzero T-count)
    operation Kernel(work : Qubit[]) : Unit {
        ApplyToEach(H, work);

        let n = Length(work);
        if (n >= 2) {
            for i in 0..n-2 {
                CNOT(work[i], work[i + 1]);
            }
        }

        // --- Non-Clifford part (drives T-count for the estimator) ---
        // T on every other qubit; safe if n is small or large.
        for i in 0..2..n-1 {
            T(work[i]);
        }
        // A few extra non-Clifford phases to bump counts slightly
        if (n > 1) { T(work[1]); }
        if (n > 3) { T(work[3]); }
        // -------------------------------------------------------------
    }

    @EntryPoint()
    operation EstimateWorkload() : Unit {
        let bitWidth = BitWidth();
        let reps     = Reps();
        use regs = Qubit[bitWidth];

        // Forward only (no functors required by the compiler profile)
        for k in 1..reps {
            Kernel(regs);
        }

        ResetAll(regs);
    }
}
