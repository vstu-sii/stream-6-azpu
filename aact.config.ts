export default {
  source: {
    type: "plantuml",
    path: "./architecture.puml",
  },
  rules: {
    acl: true,
    acyclic: true,
    apiGateway: true,
    crud: true,
    dbPerService: true,
    cohesion: true,
    stableDependencies: true,
    commonReuse: true,
  },
};
