#pragma once
// Thin extern-C facade over FEBioLib (the in-process FEBio solver API).
//
// Architecture rule (same as CascadeKit): Swift drives, C++ computes.
// This facade only forwards: it initialises the FEBio library, loads a
// .feb model, runs the solver in-process (no subprocess, no shelling
// to a febio executable), and reads back headline results from the
// solved model. It contains no FE maths of its own beyond reducing
// nodal displacements and Gauss-point stresses to maxima.

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
	int    success;       // 1 = solved, 0 = failed
	int    nNodes;        // mesh node count
	int    nElements;     // solid element count
	double maxDisp;       // max nodal displacement magnitude
	double maxVonMises;   // max von Mises stress over solid Gauss points
	double solveSeconds;  // wall time of the solve call
	char   message[1024]; // solver error/status text (never empty)
} FBResult;

// Run the model at febPath (must be in a writable directory: FEBio
// writes its .log/.xplt next to the input). Fills *out. Returns
// out->success.
int fb_run_model(const char* febPath, FBResult* out);

// FEBio version string (static storage, do not free).
const char* fb_version(void);

// Message accessor so Swift never has to touch the fixed-size char
// array inside FBResult (it imports as an opaque tuple there).
const char* fb_result_message(const FBResult* r);

#ifdef __cplusplus
}
#endif
