# Geo Expert Detector Limitations

Geo Expert can use `yolo11n.pt` as a real model path, but it remains a general object detector.

## Current Detector Scope

- model scope: `general_object_detector`
- domain specific: `false`
- legal interpretation allowed: `false`

## Domain-aware Reporting Rules

- illegal factory workflows: only report visible structures or object cues
- solar workflows: only report possible reflective or regular-array cues
- waste / dumping workflows: only report visible piles, bare areas, or anomaly cues
- disaster workflows: only report image anomalies or suspicious zones

## Not Allowed

- declaring a site to be an illegal factory
- declaring legal compliance of solar infrastructure
- declaring confirmed pollution or illegal dumping
- declaring a formal cause of disaster from detector output alone

## Production Recommendation

- keep YOLO as a visual aid
- add domain-specific training later if a dedicated detector is ever required
- retain human visual review in every enforcement-oriented workflow
