import SwiftUI

/// One-screen spike: run the bundled reference model through the
/// in-process FEBio solver (via the C facade) and show headline
/// results in large text. Big fonts, high contrast, low clutter.
struct ContentView: View {
    @State private var running = false
    @State private var status = "Ready."
    @State private var solved: Bool? = nil
    @State private var maxDisp: Double? = nil
    @State private var maxVonMises: Double? = nil
    @State private var solveSeconds: Double? = nil
    @State private var counts = ""

    private var version: String { String(cString: fb_version()) }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                Text("FEBio Spike")
                    .font(.largeTitle.bold())

                Text("Solver: \(version) — runs in-process, on this iPad.")
                    .font(.title3)

                Button {
                    runSolve()
                } label: {
                    Text(running ? "Solving…" : "Run test solve")
                        .font(.title2.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                }
                .buttonStyle(.borderedProminent)
                .disabled(running)

                Text(status)
                    .font(.title3)
                    .foregroundStyle(solved == false ? .red : .primary)
                    .fixedSize(horizontal: false, vertical: true)

                if let solved {
                    VStack(alignment: .leading, spacing: 14) {
                        resultRow("Result",
                                  solved ? "SOLVED OK" : "FAILED")
                        if !counts.isEmpty {
                            resultRow("Mesh", counts)
                        }
                        if let maxDisp {
                            resultRow("Max displacement",
                                      String(format: "%.4f mm", maxDisp))
                        }
                        if let maxVonMises {
                            resultRow("Max von Mises",
                                      String(format: "%.4f", maxVonMises))
                        }
                        if let solveSeconds {
                            resultRow("Solve time",
                                      String(format: "%.2f s", solveSeconds))
                        }
                    }
                    .padding(.top, 4)
                }

                Spacer(minLength: 12)

                Text("Reference model: 10×2×2 mm neo-Hookean block, "
                     + "left face fixed, right face pulled 1.0 mm. "
                     + "Expected max displacement: 1.0000 mm.")
                    .font(.body)
                    .foregroundStyle(.secondary)

                Text("FEBio is MIT-licensed open-source software "
                     + "(Copyright © University of Utah, the Trustees of "
                     + "Columbia University in the City of New York, and "
                     + "others). Full license: LICENSE-FEBio.txt in the "
                     + "project repository.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
            .padding(24)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func resultRow(_ label: String, _ value: String) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label)
                .font(.title3)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .font(.title3.bold())
                .monospacedDigit()
        }
    }

    private func runSolve() {
        running = true
        solved = nil
        status = "Solving…"
        DispatchQueue.global(qos: .userInitiated).async {
            let result = Solver.runBundledModel()
            DispatchQueue.main.async {
                running = false
                solved = result.success
                status = result.message
                maxDisp = result.maxDisp
                maxVonMises = result.maxVonMises
                solveSeconds = result.solveSeconds
                counts = result.counts
            }
        }
    }
}

/// Bridges to the C facade. FEBio writes its .log/.xplt next to the
/// input file, so the bundled model is first copied to a writable
/// scratch directory.
enum Solver {
    struct Outcome {
        var success: Bool
        var message: String
        var maxDisp: Double?
        var maxVonMises: Double?
        var solveSeconds: Double?
        var counts: String
    }

    static func runBundledModel() -> Outcome {
        guard let src = Bundle.main.url(forResource: "tension-block",
                                        withExtension: "feb") else {
            return Outcome(success: false,
                           message: "The bundled model file is missing from the app.",
                           maxDisp: nil, maxVonMises: nil,
                           solveSeconds: nil, counts: "")
        }
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("febio-spike", isDirectory: true)
        do {
            try FileManager.default.createDirectory(at: dir,
                                                    withIntermediateDirectories: true)
            let dst = dir.appendingPathComponent("tension-block.feb")
            if FileManager.default.fileExists(atPath: dst.path) {
                try FileManager.default.removeItem(at: dst)
            }
            try FileManager.default.copyItem(at: src, to: dst)

            var r = FBResult()
            let ok = fb_run_model(dst.path, &r)
            let msg = String(cString: fb_result_message(&r))
            guard ok == 1, r.success == 1 else {
                return Outcome(success: false, message: msg,
                               maxDisp: nil, maxVonMises: nil,
                               solveSeconds: nil, counts: "")
            }
            return Outcome(success: true, message: msg,
                           maxDisp: r.maxDisp,
                           maxVonMises: r.maxVonMises,
                           solveSeconds: r.solveSeconds,
                           counts: "\(r.nNodes) nodes, \(r.nElements) elements")
        } catch {
            return Outcome(success: false,
                           message: "Could not prepare the model file: \(error.localizedDescription)",
                           maxDisp: nil, maxVonMises: nil,
                           solveSeconds: nil, counts: "")
        }
    }
}
