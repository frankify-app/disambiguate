export default {
  extends: ["@commitlint/config-conventional"],
  // commitlint's defaultIgnores silently exempts fixup!/squash!
  // headers (measured: a fixup! commit passed the PR gate unparsed),
  // which hollows out "the type enum IS the allow-list". Off, with one
  // explicit exemption: git-generated revert headers are not
  // conventional. Merge headers get none — merge commits are allowed
  // only on main (feature branches rebase), and since this gate lints
  // only feature-branch commits, a Merge header here IS the violation.
  defaultIgnores: false,
  ignores: [(message) => message.startsWith('Revert "')],
  rules: {
    "header-max-length": [0, "always", Infinity],
    "body-max-line-length": [0, "always", Infinity],
    "footer-max-line-length": [0, "always", Infinity],
  },
};
