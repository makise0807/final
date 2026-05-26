---
name: geo-expert-workflow
description: Route geo/legal preliminary case-review requests to the Geo Expert plugin tools.
triggers:
  - 違章建築
  - 違章工廠
  - 農業區
  - 農地工廠
  - 山坡地
  - 河川區
  - 太陽能
  - 光電
  - TOD
  - 崩塌
  - 土石流
  - 綠網
  - 生態敏感
  - 衛星影像
  - 遙測
  - 地籍
  - 土地使用
preferred_tools:
  - geo_expert.run_preliminary_case_check
  - geo_expert.search_sop_database
  - geo_expert.search_legal_database
  - geo_expert.preview_satellite_overlay
  - geo_expert.open_last_outputs
  - geo_expert.handle_approval
metadata:
  hermes:
    requires_toolsets:
      - geo_expert
---

# Geo Expert Workflow

Use `geo_expert.run_preliminary_case_check` as the default entrypoint when the user asks for a geo/legal preliminary check such as:

- illegal building screening
- farmland misuse or farmland factory review
- solar panels or solar farms on farmland
- hillside overuse or collapse-risk screening
- river-zone dumping or land-use concerns
- urban planning or TOD compatibility
- ecological sensitivity or habitat review
- satellite imagery or parcel-based preliminary review

Behavior rules:

- only produce a preliminary risk report
- do not make a formal legal determination
- do not claim that a site is definitely illegal
- prefer deterministic local fixture flow when `image_case_id` or a local image is provided
- use the other `geo_expert.*` tools only when the user specifically asks for SOP search, legal search, overlay preview, reopening outputs, or recording an approval decision

Safety boundaries:

- do not do OpenEO real submit
- do not download GeoTIFF
- do not do GEE export
- do not do Drive export
- do not do Cloud Storage export
- high-risk actions must stay approval-gated
- `geo_expert.handle_approval` only records decisions and does not execute them
- if `require_satellite=true` and no real thumbnail is available, the tool must fail structurally
