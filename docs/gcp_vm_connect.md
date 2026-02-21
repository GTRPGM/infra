# GCPVM 연결 가이드라인

## SSH 생성

```bash
ssh-keygen -t ed25519 # 이후 모든 것에 yes 또는 엔터
type $env:USERPROFILE\.ssh\id_ed25519.pub # 윈도우
cat ~/.ssh/id_ed25519.pub # wsl

ssh-ed25519 AAAA.... user@DESKTOP-EM38RML
# 유저명@기기명 앞까지 복사
```

## GCP에 등록

- 프로젝트 > 사이드 바 > compute engine > vm 인스턴스 > gtrpgm-server > 수정
- ssh 키 > 항목 추가
- 위에서 복사한 키 복붙 후 이메일 입력

```bash
ssh-ed25519 AAAA.... temp@temp.com # 여기 아이디를 이후 사용
```

## 테스트

- 콘솔에서 다음 확인

```bash
ssh temp@35.216.98.244 # 위의 아이디 그대로 사용
```

## 데이터 그립 등록

- \+ > 데이터 소스 > postgre sql
- 일반에서 사용자 이름/비밀번호/db 명 입력
- ssh/ssl에서 ssh 터널 사용 > 오른쪽 문서 버튼
- 다음 대로 입력
  - 호스트: 35.216.98.244
  - 사용자 이름: 위의 아이디
  - 인증 타입: 키 쌍
  - 비공개 키 파일: ..../ssh/id_ed25519
- 연결테스트 성공시 확인
