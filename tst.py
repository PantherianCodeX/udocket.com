import os
from packages.udocket_core.agents.summarize_lib import SummarizeConfig
cfg = SummarizeConfig.from_env()
print("endpoint:", cfg.azure_openai_endpoint)
print("key_defined:", bool(cfg.azure_openai_key))
print("deployment:", cfg.azure_openai_deployment)
print("azure_enabled:", cfg.azure_enabled)
print("provider_chain:", cfg.provider_chain)