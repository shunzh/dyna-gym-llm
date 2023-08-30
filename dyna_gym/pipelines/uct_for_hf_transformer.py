from datetime import datetime
from typing import Callable, Sequence

import gym
import transformers

from dyna_gym.agents import uct
from dyna_gym.default_policy.hf_default_policy import HuggingFaceDefaultPolicy


def uct_for_hf_transformer_pipeline(
        model_name: str = None,
        model: transformers.PreTrainedModel = None,
        tokenizer: transformers.PreTrainedTokenizer = None,
        horizon: int = 100,
        reward_func: Callable = None,
        value_func: Callable = None,
        uct_args: dict = {},
        model_generation_args: dict = {},
        should_plot_tree: bool = False,
) -> Callable:
    """
    A wrapped UCT agent for HuggingFace transformer.

    Args:
        model_name: The name of a HuggingFace transformer model. If provided, will load the model and tokenizer.
        model: A HuggingFace transformer model.
        tokenizer: A HuggingFace tokenizer.
        horizon: The maximum number of steps to take.
        reward_func: A function that evaluate the reward of a sequence.
        value_func: A function that evaluate the value of a sequence.
        uct_args: Arguments for the UCT agent.
        model_generation_args: Arguments for the model generation.
        should_plot_tree: Whether to plot the tree after generation.
    """
    if model_name is not None:
        model = transformers.AutoModelForCausalLM.from_pretrained(model_name)
        tokenizer = transformers.AutoTokenizer.from_pretrained(model_name)
    else:
        assert model is not None and tokenizer is not None, \
            "Either model_name or both model and tokenizer must be provided."

    eos_token_id = tokenizer.eos_token_id

    env = gym.make('LanguageEnv-v0', terminal_token=eos_token_id, horizon=horizon, reward_func=reward_func)

    default_policy = HuggingFaceDefaultPolicy(
        env=env,
        horizon=horizon,
        model=model,
        generation_args=model_generation_args,
    )

    agent = uct.UCT(
        default_policy=default_policy,
        **uct_args
    )

    ### Run
    # FIXME doesn't support batched input
    def generate(input_str=None, input_ids=None):
        if input_str is not None:
            input_ids = tokenizer.encode(input_str, return_tensors='pt')[0]
        else:
            assert input_ids is not None, "Either input_str or input_ids must be provided."

        env.reset(input_ids)
        env.step(agent.act(env, done=False))
        output_ids_list = agent.rolled_out_trajectories

        if should_plot_tree:
            # plot (and print) the tree
            from dyna_gym.utils.tree_search_utils import plot_tree
            plot_tree(agent.root, env, tokenizer,f"tree-{datetime.now().strftime('%Y%m%d-%H%M%S')}")

        texts = [tokenizer.decode(output_ids) for output_ids in output_ids_list]

        return dict(
            output_ids=output_ids_list,
            texts=texts,
        )

    return generate
