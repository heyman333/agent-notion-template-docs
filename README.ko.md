# 📄 notion-doc

> Make your AI agent write documents like Notion — not like an AI.

[![notion-sync](https://github.com/heyman333/agent-notion-template-docs/actions/workflows/notion-sync.yml/badge.svg)](https://github.com/heyman333/agent-notion-template-docs/actions/workflows/notion-sync.yml)

[English](README.md)

AI 에이전트에게 문서를 만들어 달라고 하면 결과물이 매번 비슷합니다. 보라
그라데이션 히어로, 이모지 범벅 헤더, 그림자 달린 카드. **notion-doc** 은 그
자리에 Notion의 디자인 언어를 입히는 에이전트 skill 입니다. 요청도 내용도
그대로인데 결과만 달라집니다:

| notion-doc 없이 | notion-doc 적용 |
|---|---|
| ![before](docs/screenshot-before.png) | ![after](docs/screenshot-light.png) |

문서의 내용·목차에는 관여하지 않습니다. 구성은 내용(과 에이전트)이 정하고
skill 은 모양만 규정합니다.

## 무엇을 하나

**Notion 블록 세트**

- 이모지 페이지 아이콘, 태그 pill, 메타 줄, breadcrumb
- 콜아웃 5색: 파랑(핵심)·회색(참고)·초록(완료)·노랑(주의)·빨강(경고)
- 목차(toc), simple table, 2단 컬럼 레이아웃, 버튼 블록
- `<details>` 토글, 체크리스트(완료 취소선), 인용구, 북마크 카드
- 코드 블록 신택스 하이라이트(Prism, 라이트/다크 토큰), 인라인 코드
- Notion 텍스트 색 5종 (파랑·빨강·주황·초록·보라)
- 한글 줄바꿈(`word-break: keep-all`), 인쇄·PDF 레이아웃(`@media print`)

**비주얼 정본 하나.** 에이전트가 CSS를 새로 짓지 않습니다.
[`template.html`](skills/notion-doc/template.html) 을 복사해서 내용만 채웁니다.
본문 폭 708px, 글자색 `#37352F`, Notion 라이트/다크 팔레트를 CSS 토큰으로 넣어
뒀습니다. 다크 모드는 뷰어 테마를 자동으로 따라가고, 인쇄·PDF 로 내보내면 다시
라이트 팔레트로 돌아옵니다. 한글은 어절 중간에서 끊기지 않습니다:

| Light | Dark |
|---|---|
| ![light](docs/screenshot-light.png) | ![dark](docs/screenshot-dark.png) |

## 설치

**Claude Code (플러그인, 권장)**

```
/plugin marketplace add heyman333/agent-notion-template-docs
/plugin install notion-doc@agent-notion-template-docs
```

**Claude Code (수동 복사)**

```bash
# 프로젝트에만
cp -r skills/notion-doc <your-project>/.claude/skills/

# 모든 프로젝트에서
cp -r skills/notion-doc ~/.claude/skills/
```

**Codex, Cursor, Gemini CLI 등**

skill 은 Claude 전용 요소가 없는 평범한 파일 2개라, 지시 파일을 읽는 에이전트면
무엇이든 쓸 수 있습니다. 에이전트별 붙여넣기 스니펫(`AGENTS.md`,
`.cursor/rules`, `GEMINI.md`)은
[다른 에이전트에서 쓰기](docs/using-with-other-agents.md)를 보세요.

## 사용

설치 후에는 문서 생성 요청("~정리해서 문서로 만들어줘", "보고서 써줘",
"포스트모템 작성해줘")에 자동으로 적용됩니다. Claude Code 에서 명시적으로 부르려면:

```
/notion-doc:notion-doc
```

## 정본을 지켰는지 검사

skill 은 "CSS 를 새로 짓지 마라"고 말하지만, 말만으로는 확인이 안 됩니다. 검증기가
확인합니다 — 문서의 `<style>` 이 `template.html` 과 한 글자라도 다르면 걸립니다.

```bash
python3 skills/notion-doc/lint.py 내문서.html
```

```
✗ 내문서.html
  ERROR [css-drift] CSS 가 정본과 다르다 (1줄). CSS 를 새로 짓지 말 것 — +    box-shadow: 0 4px 12px ...
  ERROR [unknown-class] 템플릿에 없는 클래스: hero-card. 새 클래스를 만들지 말고 블록 사전에서 고를 것
```

잡는 것: 정본과 다른 CSS(그림자·그라데이션·색 변경이 전부 여기서 걸립니다), 본문의
인라인 `style` 속성과 직접 적은 색, 템플릿에 없는 클래스, `language-*` 빠진 코드
블록. 표준 라이브러리만 쓰므로 어느 에이전트에서든 CI 에서든 그냥 돌아갑니다.

**Claude Code 플러그인으로 설치했다면 자동입니다.** `PostToolUse` 훅이 HTML 을 쓸
때마다 돌려서, 어긋나면 무엇이 어떻게 틀렸는지 에이전트에게 돌려줍니다. skill 을
아예 안 거친 문서면 그 사실만 한 줄로 알려주고요. 앱·프레임워크 템플릿·빌드
산출물에는 반응하지 않습니다([게이팅 테스트](hooks/test_gating.py)).

## 결과물 예시

브라우저로 열어 보세요. 위 스크린샷은 `sample.html` 입니다.

| 파일 | 내용 | 보여주는 블록 |
|---|---|---|
| [`sample.html`](examples/sample.html) | 캠페인 제안 | 거의 모든 블록 — breadcrumb·목차·콜아웃 5색·표·2단 컬럼·토글·체크리스트·북마크·버튼 |
| [`sample-tech.html`](examples/sample-tech.html) | 장애 분석 | 코드 하이라이트, 빨간/노란 콜아웃 |
| [`sample-en.html`](examples/sample-en.html) | Campaign Proposal | `sample.html` 과 같은 구성의 영어 문서 |
| [`before.html`](examples/before.html) | 비교용 "없이" 쪽 | 에이전트 기본 출력물 |

## 구조

```
.claude-plugin/
  plugin.json          # 플러그인 매니페스트
  marketplace.json     # 마켓플레이스 카탈로그
skills/notion-doc/
  SKILL.md             # 블록 사전(어떤 내용에 어떤 블록) + 비주얼 규칙
  template.html        # 스타일 정본: Notion 블록 CSS + 라이트/다크 팔레트 토큰
  lint.py              # 정본을 지켰는지 보는 검증기 (표준 라이브러리만)
hooks/
  hooks.json           # PostToolUse — HTML 을 쓰면 자동 검증
  notion-doc-lint.py
  test_gating.py       # 훅이 반응할 자리에서만 반응하는지
examples/              # 렌더링된 예시 문서
scripts/               # 스크린샷 촬영, Notion 드리프트 감시
docs/
  using-with-other-agents.md
```

## Notion과 싱크 유지

Notion은 계속 새 블록을 내고 디자인도 예고 없이 바꿉니다. 이 repo는 거기에 매번
맞추겠다고 약속하는 대신 감시합니다. 주간
CI([`notion-sync`](.github/workflows/notion-sync.yml))가 공개 참고 페이지를 두
방식으로 다시 읽습니다. **블록 타입**은 Notion 페이지 API로(커서 페이지네이션,
블록 ~24종 감시), **굵은 스타일 토큰**(색·폭)은 headless 렌더링으로 읽어서,
커밋된 기준 [`sync/notion-snapshot.json`](sync/notion-snapshot.json)과 diff
합니다.

참고 페이지:
[Notion Block Reference — All of Notion's Blocks](https://thomasfrank.notion.site/8b40147600284c60b6f708e38f16ee68)
(Thomas Frank 의 공개 블록 동물원).

- 배지가 초록 = skill 이 지금 Notion 이 그리는 것과 일치
- 드리프트가 생기면 잡이 실패하고, 새 블록이 skill 커버 범위인지까지 적힌
  diff 가 issue 로 열립니다

참고 페이지에 블록을 더 채울수록 감시망은 공짜로 촘촘해집니다.

## 디자인 출처

비주얼 정본의 값은 눈대중이 아니라 실제 렌더링된 Notion 페이지에서 실측한
것입니다:
[Notion Block Reference — All of Notion's Blocks](https://thomasfrank.notion.site/8b40147600284c60b6f708e38f16ee68).
`template.html` 의 토큰(색·폭·radius·타이포)은 이 페이지의 computed style 을
프로브해서 얻었고, 주간 [notion-sync](#notion과-싱크-유지) 잡이 같은 페이지를
다시 실측하기 때문에 정본이 모르는 사이 낡을 일은 없습니다.

## License

[MIT](LICENSE)
