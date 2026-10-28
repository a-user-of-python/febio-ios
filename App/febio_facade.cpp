// Facade implementation over FEBioLib. See febio_facade.h.
//
// The call sequence mirrors FEBio's own FEBioApp (FEBio/FEBioApp.cpp):
// febio::InitLibrary() once, then FEBioModel::Input + febio::SolveModel.
// Results are read straight out of the solved FEModel: nodal
// displacements from node positions (m_rt - m_r0) and Cauchy stress
// from the elastic material points at each solid element's Gauss
// points, reduced to von Mises.

#include "febio_facade.h"

#include <FEBioLib/febio.h>
#include <FEBioLib/FEBioModel.h>
#include <FEBioLib/version.h>
#include <FECore/FEException.h>
#include <FECore/FEMesh.h>
#include <FECore/FENode.h>
#include <FECore/FESolidDomain.h>
#include <FECore/FEElement.h>
#include <FECore/FEMaterialPoint.h>
#include <FEBioMech/FEElasticMaterialPoint.h>

#include <chrono>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstring>

static void setMessage(FBResult* out, const char* fmt, ...)
{
	char buf[1024];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf, sizeof(buf), fmt, ap);
	va_end(ap);
	strncpy(out->message, buf, sizeof(out->message) - 1);
	out->message[sizeof(out->message) - 1] = 0;
}

static double vonMises(const mat3ds& s)
{
	const double xx = s.xx(), yy = s.yy(), zz = s.zz();
	const double xy = s.xy(), yz = s.yz(), zx = s.zx();
	const double d1 = xx - yy, d2 = yy - zz, d3 = zz - xx;
	return sqrt(0.5 * (d1 * d1 + d2 * d2 + d3 * d3) + 3.0 * (xy * xy + yz * yz + zx * zx));
}

int fb_run_model(const char* febPath, FBResult* out)
{
	memset(out, 0, sizeof(*out));
	if (febPath == nullptr || febPath[0] == 0) {
		setMessage(out, "No model path given.");
		return 0;
	}

	try {
		// One-time library init (module + material registration).
		static bool s_init = false;
		if (!s_init) {
			febio::InitLibrary();
			s_init = true;
		}

		FEBioModel fem;
		fem.CreateReport(false);

		if (fem.Input(febPath) == false) {
			setMessage(out, "FEBio could not read the model file: %s", febPath);
			return 0;
		}

		const auto t0 = std::chrono::steady_clock::now();
		const bool ok = febio::SolveModel(fem);
		const auto t1 = std::chrono::steady_clock::now();
		out->solveSeconds = std::chrono::duration<double>(t1 - t0).count();

		if (!ok) {
			setMessage(out, "FEBio solver did not converge / aborted. See the .log file written next to the model.");
			return 0;
		}

		// ---- read back results from the solved model ----------------
		FEMesh& mesh = fem.GetMesh();
		out->nNodes = mesh.Nodes();

		double maxDisp = 0.0;
		for (int i = 0; i < mesh.Nodes(); ++i) {
			const FENode& node = mesh.Node(i);
			const vec3d u = node.m_rt - node.m_r0;
			const double m = u.length();
			if (m > maxDisp) maxDisp = m;
		}
		out->maxDisp = maxDisp;

		int nElem = 0;
		double maxVM = 0.0;
		for (int d = 0; d < mesh.Domains(); ++d) {
			FEDomain& dom = mesh.Domain(d);
			FESolidDomain* sdom = dynamic_cast<FESolidDomain*>(&dom);
			if (sdom == nullptr) continue;
			for (int e = 0; e < sdom->Elements(); ++e) {
				FESolidElement& el = sdom->Element(e);
				++nElem;
				for (int g = 0; g < el.GaussPoints(); ++g) {
					FEMaterialPoint* mp = el.GetMaterialPoint(g);
					if (mp == nullptr) continue;
					FEElasticMaterialPoint* ep = mp->ExtractData<FEElasticMaterialPoint>();
					if (ep == nullptr) continue;
					const double vm = vonMises(ep->m_s);
					if (vm > maxVM) maxVM = vm;
				}
			}
		}
		out->nElements = nElem;
		out->maxVonMises = maxVM;

		out->success = 1;
		setMessage(out, "Solved OK.");
		return 1;
	}
	catch (FEException& e) {
		setMessage(out, "FEBio error: %s", e.what());
		return 0;
	}
	catch (std::exception& e) {
		setMessage(out, "Error: %s", e.what());
		return 0;
	}
	catch (...) {
		setMessage(out, "Unknown error while running FEBio.");
		return 0;
	}
}

const char* fb_version(void)
{
	static char s_buf[64];
	snprintf(s_buf, sizeof(s_buf), "FEBio %d.%d.%d", VERSION, SUBVERSION, SUBSUBVERSION);
	return s_buf;
}

const char* fb_result_message(const FBResult* r)
{
	return r ? r->message : "";
}
