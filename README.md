# 📄 notion-doc

> Make your AI agent write documents like Notion — not like an AI.

Claude Code로 문서를 만들어 달라고 하면 매번 구조도 스타일도 다른 결과물이 나옵니다.
**notion-doc** 은 Notion 제안서 템플릿을 정본으로 삼아, 어떤 세션에서 누가 요청해도
같은 구조·같은 비주얼의 문서가 나오게 하는 Claude Code skill 입니다.

| Light | Dark |
|---|---|
| ![light](docs/screenshot-light.png) | ![dark](docs/screenshot-dark.png) |

## 무엇을 고정하나

**1. 구조** — 모든 문서가 Notion 제안서의 4단 흐름을 따릅니다.

| 섹션 | 내용 |
|---|---|
| **배경** | 문서의 맥락, 목표, 범위 |
| **분석** | 연구 결과, 데이터 인사이트, 주요 고려 사항 |
| **권장 사항** | 제안된 솔루션, 전략 및 다음 단계 |
| **실행** | 액션 아이템, 타임라인, 리소스 요구 사항 |

섹션 이름은 문서 유형에 맞게 바뀝니다(버그 리포트라면 현상→원인→수정안→조치),
흐름(맥락 → 근거 → 판단 → 행동)은 유지됩니다.

**2. 비주얼** — CSS를 매번 새로 생성하지 않습니다. skill에 포함된
[`template.html`](skills/notion-doc/template.html) 스켈레톤이 스타일 정본입니다.

- 본문 폭 708px, 글자색 `#37352F` — Notion 페이지 그대로
- 이모지 페이지 아이콘 + 태그 pill 메타 줄
- 콜아웃 4색(회색/파랑/노랑/빨강), simple table, `<details>` 토글, 체크리스트
- 라이트/다크 팔레트를 CSS 토큰으로 내장 — 뷰어 테마를 자동으로 따라감

**3. 문체** — 개조식 + 짧은 평서문. 근거 없는 수식어 대신 수치와 경로를 적도록 규정.

## 설치

**플러그인으로 (권장)**

```
/plugin marketplace add heyman333/agent-notion-template-docs
/plugin install notion-doc@agent-notion-template-docs
```

**수동 복사**

```bash
# 프로젝트에만
cp -r skills/notion-doc <your-project>/.claude/skills/

# 모든 프로젝트에서
cp -r skills/notion-doc ~/.claude/skills/
```

## 사용

설치 후에는 문서 생성 요청("~정리해서 문서로 만들어줘", "제안서 써줘", "버그 리포트
작성해줘")에 skill이 자동으로 적용됩니다. 명시적으로 부르려면:

```
/notion-doc:notion-doc
```

결과물 예시는 [`examples/sample.html`](examples/sample.html) 을 브라우저로 열어 보세요 —
위 스크린샷이 이 파일입니다.

## 구조

```
.claude-plugin/
  plugin.json          # 플러그인 매니페스트
  marketplace.json     # 마켓플레이스 카탈로그
skills/notion-doc/
  SKILL.md             # 문서 규격: 구조·머리 부분·문체 규칙
  template.html        # 스타일 정본: Notion 라이트/다크 팔레트 CSS 토큰
examples/
  sample.html          # 생성 결과물 예시 (새해 캠페인 제안)
```

## 원본 템플릿

구조의 근거는 이 공개 Notion 템플릿입니다:
[새해 캠페인 제안](https://cautious-shovel-8bd.notion.site/3ccb975b320f80128e94c05534b4df9d)

## License

[MIT](LICENSE)
