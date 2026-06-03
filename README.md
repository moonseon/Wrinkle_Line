# Wrinkle Line Quantification

이미지에서 어두운 선 형태의 wrinkle을 검출해 CSV 지표로 수치화합니다.

## 사용법

1. 분석할 이미지를 준비합니다.
2. `run_wrinkle_ui.bat` 파일을 더블클릭합니다.
3. 파일 선택 창에서 분석할 이미지를 선택합니다. 여러 파일도 한 번에 선택할 수 있습니다.

결과는 선택한 이미지가 있는 폴더에 생성됩니다.

- `wrinkle_metrics.csv`: 이미지별 wrinkle 수치
- `wrinkle_overlays/*_wrinkle_overlay.png`: 빨간색은 검출 영역, 하늘색은 1-pixel skeleton 선

## PowerShell 사용법

폴더 전체를 분석하려면 아래 명령을 실행합니다.

```powershell
& 'C:\Users\moons\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' analyze_wrinkles.py . --save-overlays
```

## 노란 기준선 대비 검은 선 길이 측정

그림에 노란색 기준 라인과 검은색 측정 라인이 있는 경우:

1. `run_line_ratio_ui.bat` 파일을 더블클릭합니다.
2. 파일 선택 창에서 이미지를 선택합니다.
3. `line_ratio_metrics.csv`에서 `black_length_when_yellow_is_1` 값을 확인합니다.

이 값은 노란색 라인의 길이를 `1`로 했을 때 검은색 라인의 상대 길이입니다.
예를 들어 값이 `1.35`이면 검은색 라인이 노란색 기준선보다 1.35배 길다는 뜻입니다.

PowerShell로 실행하려면:

```powershell
& 'C:\Users\moons\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' measure_line_ratio.py "이미지파일명.jpg" --save-overlays
```

결과 파일:

- `line_ratio_metrics.csv`: 길이와 상대 비율
- `line_ratio_overlays/*_line_ratio_overlay.png`: 인식된 노란선/검은선 확인 이미지

## Streamlit 실행

웹 UI에서 이미지 파일을 선택해 계산하려면:

```powershell
streamlit run streamlit_app.py
```

GitHub 또는 Streamlit Cloud 배포에 필요한 기본 파일:

- `streamlit_app.py`
- `requirements.txt`
- `.gitignore`
- `.streamlit/config.toml`

## 주요 지표

- `wrinkle_area_pct`: ROI 면적 중 wrinkle mask 비율
- `skeleton_length_px`: wrinkle 중심선 길이의 pixel 합
- `wrinkle_density_px_per_kpx2`: 1000 pixel 면적당 wrinkle 중심선 길이
- `mean_dark_contrast`: 주변 밝기 대비 wrinkle의 어두운 정도
- `orientation_deg`: 주요 wrinkle 방향
- `orientation_strength`: 방향성이 얼마나 한 방향으로 모이는지
- `severity_index`: 면적, 길이 밀도, contrast를 합친 0-100 점수

## 옵션

ROI를 지정하려면 `x,y,width,height` 형식으로 입력합니다.

```powershell
& 'C:\Users\moons\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' analyze_wrinkles.py . --roi 120,80,640,420 --save-overlays
```

실제 단위가 필요하면 이미지의 mm/pixel 값을 넣습니다.

```powershell
& 'C:\Users\moons\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' analyze_wrinkles.py . --pixel-size-mm 0.025 --save-overlays
```

검출이 너무 많으면 `--threshold-percentile` 값을 올리고, 너무 적으면 낮춥니다.
기본값은 `86`입니다.
