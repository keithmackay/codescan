# Dependency analyzer coverage

Dependency discovery reads local manifests and lockfiles as data. It does not run a package manager, resolve ranges, contact registries, or compare installed versions with the latest release. `results.json` records the ecosystem, package name, version or constraint, whether that value was declared or resolved, a primary manifest path, and all contributing paths in `source_paths`. Identical package coordinates from multiple manifests are merged while retaining their source paths. PyPI names use the PEP 503 normalization rule for identity comparisons; NuGet IDs compare case-insensitively. Other ecosystems retain exact package-name matching. The displayed spelling is selected deterministically from the source records.

## Supported inputs

| Input | Ecosystem | Extracted evidence | Important limits |
|---|---|---|---|
| `requirements.txt` | PyPI | Lines with a package name and a comparison constraint such as `==`, `>=`, or `~=` | Ignores includes, editable installs, direct URLs, and unconstrained names. Values are declarations, not resolved installs. |
| `pyproject.toml` | PyPI | PEP 621 `project.dependencies` and optional dependency groups | Only constraints matched by the supported requirement pattern are emitted. Tool-specific dependency sections are not interpreted. |
| `poetry.lock` | PyPI | Package name and resolved version | Lockfile groups and source metadata are not represented. |
| `package-lock.json` | npm | Resolved versions from modern `packages` maps or legacy nested `dependencies` | Does not parse `npm-shrinkwrap.json`, Yarn, or pnpm lockfiles. |
| `go.mod` | Go | `require` directives, including block form | Does not resolve replacements or report indirect/transitive closure beyond listed requirements. |
| `composer.lock` | Composer | Names and versions from production and development package lists | Does not parse `composer.json` declarations. |
| `Gemfile.lock` | RubyGems | Name and version entries under the `specs` section | Does not parse `Gemfile` declarations or platform/source metadata. |
| `pom.xml` | Maven | XML `dependency` elements with group, artifact, and version | Properties remain literal (for example `${version}`); profile activation and scopes are not evaluated. |
| `*.csproj` | NuGet | `PackageReference` name and version attributes or child elements | Central package versions and imported MSBuild properties are not resolved. |
| `packages.lock.json` | NuGet | Resolved package versions grouped by target framework | Target framework and dependency type are not included in the normalized record. |

Unsupported formats include Gradle, `build.sbt`, `Pipfile.lock`, `uv.lock`, Yarn, pnpm, npm shrinkwrap, and package-manager-specific formats not listed above. This list describes parser coverage, not a statement that other formats are absent from a project.

## Status and interpretation

- `skipped`: no supported manifest was detected.
- `completed`: supported manifests were processed without parser errors. A completed parse can still produce no package records when declarations are unpinned or use unsupported syntax.
- `partial`: one or more supported manifests were too large or could not be parsed. Check the dependency parse finding and analyzer status.
- `failed`: an unexpected analyzer error occurred; other scan analyzers continue.

Vulnerability findings require the separate OSV-Scanner option. Package license metadata requires explicit online license scanning. Neither feature currently reports whether a package is behind the latest release. See [OSV-Scanner integration](OSV_SCANNER.md) for vulnerability and license data behavior.
