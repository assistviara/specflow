"""Explicit Human test policy shared by Plan and implementation inputs."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TddPolicy:
    required: bool
    rules: str
    no_tdd_reason: str | None = None

    def validate(self):
        if type(self.required) is not bool or not isinstance(self.rules, str) or not self.rules.strip():
            raise ValueError('Explicit TDD selection and rules are required; STOP.')
        if self.required and self.no_tdd_reason is not None:
            raise ValueError('TDD required conflicts with non-applicability reason; STOP.')
        if not self.required and (not isinstance(self.no_tdd_reason, str) or not self.no_tdd_reason.strip()):
            raise ValueError('Formal TDD non-applicability reason is required; STOP.')
        return self

    def instruction(self):
        self.validate()
        order = ('Create tests -> confirm initial failure -> implement -> confirm success.'
                 if self.required else 'TDD is explicitly not required. Do not invent a test-first requirement.')
        return (f'\n## Explicit Human TDD policy\nTDD required: {self.required}\n'
                f'Rules: {self.rules}\nNon-applicability reason: {self.no_tdd_reason}\n'
                f'{order}\nReflect this policy in the Plan implementation steps and test plan. '
                'Do not infer missing decisions. Report conflicts for Human review.\n')


def require_tdd_policy(policy):
    if not isinstance(policy, TddPolicy):
        raise ValueError('TDD policy must be decided before Plan generation; STOP.')
    return policy.validate()
