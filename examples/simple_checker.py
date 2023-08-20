from fulgens import Verdict, ChallengeHelper
from pathlib import Path

def do_check(helper: ChallengeHelper) -> Verdict:
    try:
        print(helper.run("nginx", "ls -la"))
        print(helper.run("nginx", "ls -la && pwd"))
        print(helper.run("nginx", ["pwd", "cd /etc", "pwd"]))
        helper.fetch("nginx", "/etc/nginx", helper.local_chall_dir)
        helper.fetch("nginx", "/etc/nginx/conf.d/default.conf", helper.local_chall_dir)
    except Exception as ex:
        return Verdict.ERROR(ex)
    return Verdict.OK()

if __name__ == "__main__":
    helper = ChallengeHelper(
        addresses=["127.0.0.1:8080"],
        secret="Secret2023",
        local_challenge_dir=Path(__file__).parent,
        compose_filename="docker-compose.yml",
    )

    verdict = do_check(helper)
    print("Verdict:", verdict.status)
    print("Message:", verdict.message)