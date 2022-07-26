from behave import use_step_matcher

use_step_matcher("cfparse")


def before_all(context):
    context.config.setup_logging()
