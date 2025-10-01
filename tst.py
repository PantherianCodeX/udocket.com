from packages.udocket_core.agents.summarize_lib import SummarizeConfig


cfg = SummarizeConfig.from_env()
print("provider_chain:", cfg.provider_chain)
print("language:", cfg.language)
print("max_output_tokens:", cfg.max_output_tokens)
