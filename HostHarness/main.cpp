// Host harness: drives the app facade (App/febio_facade.cpp) through
// the in-process FEBioLib API on the bundled reference model and
// prints the headline numbers. This is the exact code path the iPad
// app runs; the numbers printed here are the on-device targets.
//
// Usage: febio_host_harness <model.feb>
#include "../App/febio_facade.h"
#include <cstdio>

int main(int argc, char** argv)
{
	if (argc < 2) {
		printf("usage: %s <model.feb>\n", argv[0]);
		return 2;
	}
	printf("library: %s\n", fb_version());
	FBResult r;
	const int ok = fb_run_model(argv[1], &r);
	printf("success     : %d\n", r.success);
	printf("message     : %s\n", r.message);
	printf("nodes       : %d\n", r.nNodes);
	printf("elements    : %d\n", r.nElements);
	printf("maxDisp     : %.9g\n", r.maxDisp);
	printf("maxVonMises : %.9g\n", r.maxVonMises);
	printf("solveSeconds: %.3f\n", r.solveSeconds);
	return ok ? 0 : 1;
}
