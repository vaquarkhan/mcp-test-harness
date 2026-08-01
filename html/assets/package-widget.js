/**
 * Live PyPI version + download badges for all 23 harness packages.
 * Used on integrations.html (MCP-Bastion-style download widget).
 */
(function () {
  const PKGS = [
    ['mcp-test-harness', 'Core CLI + assertions'],
    ['mcp-test-harness-openai', 'OpenAI GPT'],
    ['mcp-test-harness-anthropic', 'Anthropic Claude'],
    ['mcp-test-harness-bedrock', 'AWS Bedrock'],
    ['mcp-test-harness-gemini', 'Google Gemini'],
    ['mcp-test-harness-azure', 'Azure OpenAI'],
    ['mcp-test-harness-vertexai', 'Vertex AI'],
    ['mcp-test-harness-langchain', 'LangChain'],
    ['mcp-test-harness-llamaindex', 'LlamaIndex'],
    ['mcp-test-harness-crewai', 'CrewAI'],
    ['mcp-test-harness-fastmcp', 'FastMCP servers'],
    ['mcp-test-harness-autogen', 'Microsoft AutoGen'],
    ['mcp-test-harness-groq', 'Groq'],
    ['mcp-test-harness-mistral', 'Mistral AI'],
    ['mcp-test-harness-cohere', 'Cohere'],
    ['mcp-test-harness-huggingface', 'Hugging Face'],
    ['mcp-test-harness-deepseek', 'DeepSeek AI'],
    ['mcp-test-harness-together', 'Together AI'],
    ['mcp-test-harness-fireworks', 'Fireworks AI'],
    ['mcp-test-harness-ollama', 'Ollama'],
    ['mcp-test-harness-openrouter', 'OpenRouter'],
    ['mcp-test-harness-litellm', 'LiteLLM'],
    ['mcp-test-harness-xai', 'xAI Grok'],
  ];

  function render() {
    const tbody = document.getElementById('pypi-widget-body');
    if (!tbody) return;

    tbody.replaceChildren();
    PKGS.forEach(([name, label]) => {
      const tr = document.createElement('tr');
      tr.className = 'pypi-widget-row';
      tr.innerHTML = `
        <td class="pypi-widget-name"><a href="https://pypi.org/project/${name}/" target="_blank" rel="noopener noreferrer">${name}</a></td>
        <td class="pypi-widget-label">${label}</td>
        <td class="pypi-widget-version"><a href="https://pypi.org/project/${name}/" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/pypi/v/${name}?label=version&amp;color=indigo" alt="PyPI ${name}" height="20" loading="lazy" /></a></td>
        <td class="pypi-widget-dl"><a href="https://pepy.tech/project/${name}" target="_blank" rel="noopener noreferrer"><img src="https://static.pepy.tech/badge/${name}" alt="Downloads ${name}" height="20" loading="lazy" /></a></td>
        <td class="pypi-widget-cmd"><code>pip install ${name}</code></td>`;
      tbody.appendChild(tr);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
