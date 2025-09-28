namespace FallbackKernel {
    open Microsoft.Quantum.Intrinsic;
    open Microsoft.Quantum.Canon;

    internal function BitWidth() : Int { return 128; }
    internal function Reps()    : Int { return 4;   }

    operation Kernel(work : Qubit[]) : Unit {
        ApplyToEach(H, work);
        let n = Length(work);
        if (n >= 2) {
            for i in 0..n-2 {
                CNOT(work[i], work[i + 1]);
            }
        }
        // Non-Clifford pressure for estimator
        for i in 0..2..n-1 { T(work[i]); }
        if (n > 1) { T(work[1]); }
        if (n > 3) { T(work[3]); }
    }

    @EntryPoint()
    operation EstimateWorkload() : Unit {
        let bitWidth = BitWidth();
        let reps     = Reps();
        use regs = Qubit[bitWidth];
        for _ in 1..reps { Kernel(regs); }
        ResetAll(regs);
    }
}
