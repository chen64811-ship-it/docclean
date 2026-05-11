# -*- coding: utf-8 -*-
"""
DocClean License Key 生成工具
==============================
仅供卖方使用：为客户生成 License Key。

用法：
    python generate_license.py --type pro --email "customer@example.com" --expiry 2026-12-31
    python generate_license.py --type enterprise --email "corp@bigbank.com" --expiry 2027-06-30
    python generate_license.py --type pro --email "test@test.com" --expiry 2026-06-30 --count 5
"""

import sys
import os

# 允许从命令行直接运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.license_service import generate_license_key, verify_license_key


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="DocClean License Key Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_license.py --type pro --email "user@example.com" --expiry 2026-12-31
  python generate_license.py --type enterprise --email "corp@bigbank.com" --expiry 2027-06-30
  python generate_license.py --type pro --email "test@test.com" --expiry 2026-06-30 --count 10
        """
    )
    parser.add_argument("--type", required=True, choices=["pro", "enterprise"],
                        help="License tier: pro or enterprise")
    parser.add_argument("--email", required=True,
                        help="Customer email address")
    parser.add_argument("--expiry", required=True,
                        help="Expiry date (YYYY-MM-DD)")
    parser.add_argument("--count", type=int, default=1,
                        help="Number of keys to generate (default: 1)")

    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  DocClean License Key Generator")
    print("=" * 60)
    print(f"  Tier:     {args.type.upper()}")
    print(f"  Customer: {args.email}")
    print(f"  Expiry:   {args.expiry}")
    print(f"  Count:    {args.count}")
    print("=" * 60)
    print()

    for i in range(args.count):
        key = generate_license_key(args.type, args.expiry, args.email)
        # 验证生成的 Key
        verified = verify_license_key(key)
        status = "VALID" if verified else "INVALID"
        print(f"  [{i+1}] [{status}] {key}")

    print()
    print("  Send the key to the customer. They activate it at:")
    print("  Settings → License → Enter Key → Activate")
    print()


if __name__ == "__main__":
    main()
