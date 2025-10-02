from packages.udocket_core.agents.analyze_lib import AnalyzeConfig


cfg = AnalyzeConfig.from_env()
print("provider_chain:", cfg.provider_chain)
print("language:", cfg.language)
print("max_output_tokens:", cfg.max_output_tokens)
