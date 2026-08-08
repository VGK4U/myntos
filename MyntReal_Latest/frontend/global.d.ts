declare module 'mermaid' {
  const mermaid: {
    initialize: (config: Record<string, unknown>) => void;
    contentLoaded: () => void;
    default: {
      initialize: (config: Record<string, unknown>) => void;
      contentLoaded: () => void;
    };
  };
  export default mermaid;
}

declare module '*.css' {
  const content: Record<string, string>;
  export default content;
}
