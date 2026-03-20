---
title: "Manual Review Showcase — English"
---

<!-- docx:page_footer.left -->
Confidential

<!-- docx:page_footer.center -->
Manual Review

<!-- docx:page_footer.right -->
English Showcase

# Manual Review Showcase

This opening paragraph is meant to render with the lead paragraph treatment so
it is visually distinct from the rest of the body copy.

## Styled Benchmark Table

<!-- docx:id=wide-table -->
| Scenario | Prompt Tokens | Output Tokens | TTFT (ms) | TPS |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 20K | 1K | 497 | 197.9 |
| Steady State | 20K | 2K | 596 | 139.4 |
| Stress | 30K | 2K | 1182 | 101.0 |

## Notes

- Bullet one with **bold** detail
- Bullet two with *italic* note

> This blockquote should survive as a visually distinct callout in Google Docs.

```python
def summarize_latency(values: list[int]) -> float:
    return sum(values) / len(values)
```

## Compact Comparison Table

<!-- docx:id=compact-table -->
| GPU | Status | Owner |
| :--- | :---: | ---: |
| B200 | PASS | Alice |
| B300 | WARN | Bob |

## Images and Bilingual Copy

![Tiny Example](tiny.png)

This paragraph mixes English and 中文 to verify the chosen font slots remain
usable after Google Docs import.

<!-- docx:id=appendix-break -->
## Appendix

This appendix heading should start on a new page in the generated DOCX.
