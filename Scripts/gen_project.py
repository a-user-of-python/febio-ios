#!/usr/bin/env python3
"""Generate FEBioSpike.xcodeproj (deterministic).

Single target: the FEBio Spike SwiftUI app (com.user.febiospike).
The FEBio solver itself is cross-compiled ahead of time by
Scripts/build-febio-ios.sh into build/febio/lib/*.a and force-loaded
into the app binary — FEBio registers its modules/materials through
static initialisers spread across those archives, so every object
must be pulled in (-force_load), exactly like a shared-library load.

UUIDs are md5-derived from stable keys, so regenerating produces a
byte-identical project. Run:  python3 Scripts/gen_project.py
"""
import hashlib
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ_DIR = os.path.join(ROOT, "FEBioSpike.xcodeproj")

_used = set()


def U(key):
    h = hashlib.md5(key.encode()).hexdigest()[:24].upper()
    assert h not in _used, f"uuid collision: {key}"
    _used.add(h)
    return h


APP_SOURCES = [
    "App/FEBioSpikeApp.swift",
    "App/ContentView.swift",
    "App/febio_facade.cpp",
]
APP_OTHER = [
    "App/febio_facade.h",
    "App/FEBioSpike-Bridging-Header.h",
    "App/Info.plist",
]
APP_RESOURCES = ["Model/tension-block.feb"]

# FEBio static archives produced by Scripts/build-febio-ios.sh.
FEBIO_LIBS = [
    "febiolib", "febiofluid", "febiomech", "febiomix", "febioopt",
    "febioplot", "febioxml", "feamr", "febiorve", "feimglib",
    "numcore", "fecore",
]

FILETYPE = {
    "cpp": "sourcecode.cpp.cpp",
    "h": "sourcecode.c.h",
    "swift": "sourcecode.swift",
    "plist": "text.plist.xml",
    "feb": "text",
}

fileref_id = {}
buildfile_id = {}


def fileref(path):
    if path not in fileref_id:
        fileref_id[path] = U("fileref:" + path)
    return fileref_id[path]


def buildfile(path, phase):
    key = (path, phase)
    if key not in buildfile_id:
        buildfile_id[key] = U(f"buildfile:{phase}:{path}")
    return buildfile_id[key]


ALL_PATHS = APP_SOURCES + APP_OTHER + APP_RESOURCES
for p in ALL_PATHS:
    fileref(p)
for p in APP_SOURCES:
    buildfile(p, "app-sources")
for p in APP_RESOURCES:
    buildfile(p, "app-resources")

APP_REF = U("product:FEBioSpike.app")
APP_TARGET = U("target:FEBioSpike")
APP_SOURCES_PHASE = U("phase:app-sources")
APP_FRAMEWORKS_PHASE = U("phase:app-frameworks")
APP_RESOURCES_PHASE = U("phase:app-resources")
PROJECT = U("project:FEBioSpike")
MAIN_GROUP = U("group:main")
APP_GROUP = U("group:App")
MODEL_GROUP = U("group:Model")
PRODUCTS_GROUP = U("group:Products")
PROJ_CFG_LIST = U("cfglist:project")
APP_CFG_LIST = U("cfglist:app")
PROJ_DEBUG = U("cfg:project:Debug")
PROJ_RELEASE = U("cfg:project:Release")
APP_DEBUG = U("cfg:app:Debug")
APP_RELEASE = U("cfg:app:Release")

out = []


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def q(s):
    # Conservative quoting (see cascade-ios gen_project.py): quote
    # anything outside [A-Za-z0-9_./-] so Xcode's plist parser accepts
    # the file.
    if s and all(c.isalnum() or c in "_./-" for c in s):
        return s
    return '"' + esc(s) + '"'


def fileref_line(path):
    ext = path.rsplit(".", 1)[-1]
    name = os.path.basename(path)
    return (f"\t\t{fileref(path)} /* {name} */ = {{isa = PBXFileReference; "
            f"lastKnownFileType = {FILETYPE[ext]}; name = {q(name)}; "
            f"path = {q(path)}; sourceTree = SOURCE_ROOT; }};")


def buildfile_line(path, phase):
    name = os.path.basename(path)
    return (f"\t\t{buildfile(path, phase)} /* {name} in {phase} */ = "
            f"{{isa = PBXBuildFile; fileRef = {fileref(path)} /* {name} */; }};")


def settings_block(d, indent="\t\t\t\t"):
    lines = []
    for k in sorted(d):
        v = d[k]
        if isinstance(v, list):
            lines.append(f"{indent}{k} = (")
            for item in v:
                lines.append(f"{indent}\t{q(item)},")
            lines.append(f"{indent});")
        else:
            lines.append(f"{indent}{k} = {q(v)};")
    return lines


def config(cid, name, settings):
    lines = [f"\t\t{cid} /* {name} */ = {{",
             "\t\t\tisa = XCBuildConfiguration;",
             "\t\t\tbuildSettings = {"]
    lines += settings_block(settings)
    lines += ["\t\t\t};", f"\t\t\tname = {name};", "\t\t};"]
    return lines


def main():
    ldflags = ["$(inherited)", "-lc++", "-lz"]
    for lib in FEBIO_LIBS:
        ldflags += ["-force_load", f"$(SRCROOT)/build/febio/lib/lib{lib}.a"]

    proj_common = {
        "ALWAYS_SEARCH_USER_PATHS": "NO",
        "CLANG_CXX_LANGUAGE_STANDARD": "gnu++17",
        "CLANG_ENABLE_MODULES": "YES",
        "GCC_ENABLE_CPP_EXCEPTIONS": "YES",
        "GCC_ENABLE_CPP_RTTI": "YES",
        "IPHONEOS_DEPLOYMENT_TARGET": "17.0",
        "SDKROOT": "iphoneos",
        "TARGETED_DEVICE_FAMILY": "2",
    }
    app_settings = {
        "ARCHS": "arm64",
        "CODE_SIGN_STYLE": "Automatic",
        "CURRENT_PROJECT_VERSION": "1",
        "DEVELOPMENT_TEAM": "",
        "GENERATE_INFOPLIST_FILE": "NO",
        "HEADER_SEARCH_PATHS": [
            "$(inherited)",
            "$(SRCROOT)/App",
            "$(SRCROOT)/build/febio/src",
            "$(SRCROOT)/build/febio/src/FEBioLib",
        ],
        "INFOPLIST_FILE": "App/Info.plist",
        "MARKETING_VERSION": "1.0",
        "OTHER_LDFLAGS": ldflags,
        "PRODUCT_BUNDLE_IDENTIFIER": "com.user.febiospike",
        "PRODUCT_NAME": "FEBioSpike",
        "SWIFT_OBJC_BRIDGING_HEADER": "App/FEBioSpike-Bridging-Header.h",
        "SWIFT_VERSION": "5.0",
        "TARGETED_DEVICE_FAMILY": "2",
    }

    o = out.append
    o("// !$*UTF8*$!")
    o("{")
    o("\tarchiveVersion = 1;")
    o("\tclasses = {")
    o("\t};")
    o("\tobjectVersion = 56;")
    o("\tobjects = {")
    o("")

    o("/* Begin PBXBuildFile section */")
    for p in APP_SOURCES:
        o(buildfile_line(p, "app-sources"))
    for p in APP_RESOURCES:
        o(buildfile_line(p, "app-resources"))
    o("/* End PBXBuildFile section */")
    o("")

    o("/* Begin PBXFileReference section */")
    for p in ALL_PATHS:
        o(fileref_line(p))
    o(f"\t\t{APP_REF} /* FEBioSpike.app */ = {{isa = PBXFileReference; "
      "explicitFileType = wrapper.application; includeInIndex = 0; "
      "path = FEBioSpike.app; sourceTree = BUILT_PRODUCTS_DIR; };")
    o("/* End PBXFileReference section */")
    o("")

    o("/* Begin PBXFrameworksBuildPhase section */")
    o(f"\t\t{APP_FRAMEWORKS_PHASE} /* Frameworks */ = {{")
    o("\t\t\tisa = PBXFrameworksBuildPhase;")
    o("\t\t\tbuildActionMask = 2147483647;")
    o("\t\t\tfiles = (")
    o("\t\t\t);")
    o("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    o("\t\t};")
    o("/* End PBXFrameworksBuildPhase section */")
    o("")

    o("/* Begin PBXResourcesBuildPhase section */")
    o(f"\t\t{APP_RESOURCES_PHASE} /* Resources */ = {{")
    o("\t\t\tisa = PBXResourcesBuildPhase;")
    o("\t\t\tbuildActionMask = 2147483647;")
    o("\t\t\tfiles = (")
    for p in APP_RESOURCES:
        o(f"\t\t\t\t{buildfile(p, 'app-resources')} /* {os.path.basename(p)} in Resources */,")
    o("\t\t\t);")
    o("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    o("\t\t};")
    o("/* End PBXResourcesBuildPhase section */")
    o("")

    o("/* Begin PBXSourcesBuildPhase section */")
    o(f"\t\t{APP_SOURCES_PHASE} /* Sources */ = {{")
    o("\t\t\tisa = PBXSourcesBuildPhase;")
    o("\t\t\tbuildActionMask = 2147483647;")
    o("\t\t\tfiles = (")
    for p in APP_SOURCES:
        o(f"\t\t\t\t{buildfile(p, 'app-sources')} /* {os.path.basename(p)} in Sources */,")
    o("\t\t\t);")
    o("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    o("\t\t};")
    o("/* End PBXSourcesBuildPhase section */")
    o("")

    o("/* Begin PBXGroup section */")

    def group(gid, name, children, path=None):
        o(f"\t\t{gid} /* {name} */ = {{")
        o("\t\t\tisa = PBXGroup;")
        o("\t\t\tchildren = (")
        for cid, cname in children:
            o(f"\t\t\t\t{cid} /* {cname} */,")
        o("\t\t\t);")
        if path:
            o(f"\t\t\tpath = {q(path)};")
        o(f"\t\t\tname = {q(name)};")
        o("\t\t\tsourceTree = \"<group>\";")
        o("\t\t};")

    group(APP_GROUP, "App",
          [(fileref(p), os.path.basename(p)) for p in APP_SOURCES + APP_OTHER])
    group(MODEL_GROUP, "Model",
          [(fileref(p), os.path.basename(p)) for p in APP_RESOURCES])
    group(PRODUCTS_GROUP, "Products", [(APP_REF, "FEBioSpike.app")])
    group(MAIN_GROUP, "Main",
          [(APP_GROUP, "App"), (MODEL_GROUP, "Model"),
           (PRODUCTS_GROUP, "Products")])
    o("/* End PBXGroup section */")
    o("")

    o("/* Begin PBXNativeTarget section */")
    o(f"\t\t{APP_TARGET} /* FEBioSpike */ = {{")
    o("\t\t\tisa = PBXNativeTarget;")
    o(f"\t\t\tbuildConfigurationList = {APP_CFG_LIST} /* Build configuration list for PBXNativeTarget \"FEBioSpike\" */;")
    o("\t\t\tbuildPhases = (")
    o(f"\t\t\t\t{APP_SOURCES_PHASE} /* Sources */,")
    o(f"\t\t\t\t{APP_FRAMEWORKS_PHASE} /* Frameworks */,")
    o(f"\t\t\t\t{APP_RESOURCES_PHASE} /* Resources */,")
    o("\t\t\t);")
    o("\t\t\tbuildRules = ();")
    o("\t\t\tdependencies = ();")
    o("\t\t\tname = FEBioSpike;")
    o("\t\t\tproductName = FEBioSpike;")
    o(f"\t\t\tproductReference = {APP_REF} /* FEBioSpike.app */;")
    o("\t\t\tproductType = \"com.apple.product-type.application\";")
    o("\t\t};")
    o("/* End PBXNativeTarget section */")
    o("")

    o("/* Begin PBXProject section */")
    o(f"\t\t{PROJECT} /* Project object */ = {{")
    o("\t\t\tisa = PBXProject;")
    o("\t\t\tattributes = {")
    o("\t\t\t\tBuildIndependentTargetsInParallel = 1;")
    o("\t\t\t\tLastUpgradeCheck = 1500;")
    o("\t\t\t\tTargetAttributes = {")
    o(f"\t\t\t\t\t{APP_TARGET} = {{")
    o("\t\t\t\t\t\tCreatedOnToolsVersion = 15.0;")
    o("\t\t\t\t\t};")
    o("\t\t\t\t};")
    o("\t\t\t};")
    o(f"\t\t\tbuildConfigurationList = {PROJ_CFG_LIST} /* Build configuration list for PBXProject \"FEBioSpike\" */;")
    o("\t\t\tcompatibilityVersion = \"Xcode 14.0\";")
    o("\t\t\tdevelopmentRegion = en;")
    o("\t\t\thasScannedForEncodings = 0;")
    o("\t\t\tknownRegions = (")
    o("\t\t\t\ten,")
    o("\t\t\t\tBase,")
    o("\t\t\t);")
    o(f"\t\t\tmainGroup = {MAIN_GROUP};")
    o(f"\t\t\tproductRefGroup = {PRODUCTS_GROUP} /* Products */;")
    o("\t\t\tprojectDirPath = \"\";")
    o("\t\t\tprojectRoot = \"\";")
    o("\t\t\ttargets = (")
    o(f"\t\t\t\t{APP_TARGET} /* FEBioSpike */,")
    o("\t\t\t);")
    o("\t\t};")
    o("/* End PBXProject section */")
    o("")

    o("/* Begin XCBuildConfiguration section */")
    for cid, name, st in [(PROJ_DEBUG, "Debug", proj_common),
                          (PROJ_RELEASE, "Release", proj_common)]:
        for line in config(cid, name, st):
            o(line)
    for cid, name, st in [(APP_DEBUG, "Debug", app_settings),
                          (APP_RELEASE, "Release", app_settings)]:
        for line in config(cid, name, st):
            o(line)
    o("/* End XCBuildConfiguration section */")
    o("")

    o("/* Begin XCConfigurationList section */")
    for cid, what, ids in [
            (PROJ_CFG_LIST, 'PBXProject "FEBioSpike"', (PROJ_DEBUG, PROJ_RELEASE)),
            (APP_CFG_LIST, 'PBXNativeTarget "FEBioSpike"', (APP_DEBUG, APP_RELEASE))]:
        o(f"\t\t{cid} /* Build configuration list for {what} */ = {{")
        o("\t\t\tisa = XCConfigurationList;")
        o("\t\t\tbuildConfigurations = (")
        for i, n in zip(ids, ("Debug", "Release")):
            o(f"\t\t\t\t{i} /* {n} */,")
        o("\t\t\t);")
        o("\t\t\tdefaultConfigurationIsVisible = 0;")
        o("\t\t\tdefaultConfigurationName = Release;")
        o("\t\t};")
    o("/* End XCConfigurationList section */")
    o("\t};")
    o(f"\trootObject = {PROJECT} /* Project object */;")
    o("}")

    os.makedirs(PROJ_DIR, exist_ok=True)
    with open(os.path.join(PROJ_DIR, "project.pbxproj"), "w") as f:
        f.write("\n".join(out) + "\n")

    buildable = (
        '            <BuildableReference\n'
        '               BuildableIdentifier = "primary"\n'
        f'               BlueprintIdentifier = "{APP_TARGET}"\n'
        '               BuildableName = "FEBioSpike.app"\n'
        '               BlueprintName = "FEBioSpike"\n'
        '               ReferencedContainer = "container:FEBioSpike.xcodeproj">\n'
        '            </BuildableReference>')
    scheme = f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme
   LastUpgradeVersion = "1600"
   version = "1.7">
   <BuildAction
      parallelizeBuildables = "YES"
      buildImplicitDependencies = "YES"
      buildArchitectures = "Automatic">
      <BuildActionEntries>
         <BuildActionEntry
            buildForTesting = "YES"
            buildForRunning = "YES"
            buildForProfiling = "YES"
            buildForArchiving = "YES"
            buildForAnalyzing = "YES">
{buildable}
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
   <TestAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      shouldUseLaunchSchemeArgsEnv = "YES"
      shouldAutocreateTestPlan = "YES">
      <Testables>
      </Testables>
   </TestAction>
   <LaunchAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      launchStyle = "0"
      useCustomWorkingDirectory = "NO"
      ignoresPersistentStateOnLaunch = "NO"
      debugDocumentVersioning = "YES"
      debugServiceExtension = "internal"
      allowLocationSimulation = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
{buildable}
      </BuildableProductRunnable>
   </LaunchAction>
   <ProfileAction
      buildConfiguration = "Release"
      shouldUseLaunchSchemeArgsEnv = "YES"
      savedToolIdentifier = ""
      useCustomWorkingDirectory = "NO"
      debugDocumentVersioning = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
{buildable}
      </BuildableProductRunnable>
   </ProfileAction>
   <AnalyzeAction
      buildConfiguration = "Debug">
   </AnalyzeAction>
   <ArchiveAction
      buildConfiguration = "Release"
      revealArchiveInOrganizer = "YES">
   </ArchiveAction>
</Scheme>
'''
    schemes_dir = os.path.join(PROJ_DIR, "xcshareddata", "xcschemes")
    os.makedirs(schemes_dir, exist_ok=True)
    with open(os.path.join(schemes_dir, "FEBioSpike.xcscheme"), "w") as f:
        f.write(scheme)

    ws_dir = os.path.join(PROJ_DIR, "project.xcworkspace")
    os.makedirs(ws_dir, exist_ok=True)
    with open(os.path.join(ws_dir, "contents.xcworkspacedata"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<Workspace\n'
                '   version = "1.0">\n'
                '   <FileRef\n'
                '      location = "self:">\n'
                '   </FileRef>\n'
                '</Workspace>\n')

    print(f"FEBioSpike.xcodeproj generated ({len(out)} lines)")


if __name__ == "__main__":
    main()
