#!/usr/bin/env python3
"""
ClickOps-Or-Terraform - Detect Azure resources created manually via portal clicks vs Infrastructure as Code

Copyright (c) 2024 Ed Crotty (ecrotty@edcrotty.com)
Licensed under the BSD 3-Clause License. See LICENSE file for details.

This script identifies Azure resources created through the portal (click-ops) by analyzing
resource metadata and creation patterns. It provides a clear, user-friendly output of
resources that were likely created manually rather than through automation.

Features:
- Detects portal-created resources through metadata analysis
- Provides clear, formatted output for easy reading
- Supports single or multiple subscription analysis
- Identifies resources based on multiple detection methods
- Exports results to CSV for further analysis
"""

import json
import subprocess
import sys
import csv
import argparse
from datetime import datetime
from typing import Dict, List, Any
import textwrap

# Define the full path to Azure CLI
AZ_CLI_PATH = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze Azure resources to identify those created through the portal (click-ops).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              %(prog)s                     # Run analysis with interactive subscription selection
              %(prog)s --output results.csv # Export results to CSV file
        """)
    )
    parser.add_argument(
        '--output',
        help='Export results to specified CSV file (e.g., results.csv)',
        type=str
    )
    return parser.parse_args()

def check_az_cli():
    """
    Check if Azure CLI is installed and accessible.
    """
    try:
        subprocess.check_output([AZ_CLI_PATH, '--version'], stderr=subprocess.STDOUT)
    except FileNotFoundError:
        print("❌ Error: Azure CLI is not installed or not found in PATH.")
        sys.exit(1)

def ensure_az_login():
    """
    Ensure the user is logged into Azure CLI. If not, prompt for login.
    """
    try:
        subprocess.check_output([AZ_CLI_PATH, 'account', 'show'], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        print("🔑 Azure CLI is not logged in. Attempting to log in...")
        try:
            subprocess.check_call([AZ_CLI_PATH, 'login'])
            print("✅ Azure CLI login successful.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error: Azure login failed. Details: {e}")
            sys.exit(1)

def get_subscriptions():
    """
    Fetch all available Azure subscriptions.
    Returns a list of subscription IDs and their names.
    """
    try:
        subscriptions_json = subprocess.check_output([AZ_CLI_PATH, 'account', 'list', '-o', 'json'])
        subscriptions = json.loads(subscriptions_json)
        return [(sub['id'], sub['name']) for sub in subscriptions]
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: Unable to fetch subscriptions. Details: {e}")
        sys.exit(1)

def select_subscription(subscriptions):
    """
    Prompt the user to select a subscription or evaluate all.
    Returns a list of subscription IDs to evaluate.
    """
    print("\n📋 Available Subscriptions:")
    for idx, (_, name) in enumerate(subscriptions):
        print(f"  {idx + 1}: {name}")
    print(f"  {len(subscriptions) + 1}: Evaluate all subscriptions")

    while True:
        try:
            choice = int(input("\n📎 Select a subscription (enter the number): "))
            if choice == len(subscriptions) + 1:
                return [sub[0] for sub in subscriptions]
            elif 1 <= choice <= len(subscriptions):
                return [subscriptions[choice - 1][0]]
        except ValueError:
            pass
        print("❌ Invalid choice. Please try again.")

def fetch_resource_details(subscription_id):
    """
    Fetch detailed information about all Azure resources for a given subscription.
    Returns a list of resources with their metadata.
    """
    try:
        # Single-line query string
        query = "[].{id:id, name:name, type:type, resourceGroup:resourceGroup, tags:tags, createdTime:createdTime, createdBy:identity.principalId, managedBy:managedBy, identity:identity, provisioningState:provisioningState}"
        
        az_resources_json = subprocess.check_output(
            [AZ_CLI_PATH, 'resource', 'list', 
             '--subscription', subscription_id,
             '--query', query,
             '-o', 'json']
        )
        return json.loads(az_resources_json)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: Failed to fetch resources for subscription {subscription_id}. Details: {e}")
        sys.exit(1)

def is_portal_created(resource: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Determine if a resource was created through the Azure portal by checking multiple indicators.
    Returns a tuple of (is_portal_created, reasons).
    """
    reasons = []
    
    # Check for azurerm in various metadata fields
    identity = resource.get('identity', {}) or {}
    managed_by = resource.get('managedBy', '')
    created_by = resource.get('createdBy', '')
    
    if isinstance(identity, dict) and 'azurerm' in str(identity).lower():
        reasons.append("Resource identity contains 'azurerm' identifier")
    
    if managed_by and 'azurerm' in managed_by.lower():
        reasons.append("Resource managedBy field contains 'azurerm'")
        
    if created_by and 'azurerm' in created_by.lower():
        reasons.append("Resource createdBy field contains 'azurerm'")

    # Check for absence of automation tags
    tags = resource.get('tags', {}) or {}
    automation_indicators = {
        'terraform',
        'arm-template',
        'bicep',
        'pulumi',
        'cloudformation',
        'managed-by',
        'created-by',
        'provisioner',
        'environment',
        'automation'
    }
    
    tags_lower = {k.lower(): str(v).lower() for k, v in tags.items()}
    has_automation_tags = any(
        indicator in k or indicator in v 
        for k, v in tags_lower.items() 
        for indicator in automation_indicators
    )
    
    if not tags:
        reasons.append("Resource has no tags")
    elif not has_automation_tags:
        reasons.append("Resource lacks automation-related tags")

    # Check for manual provisioning indicators
    provisioning_state = resource.get('provisioningState', '').lower()
    if provisioning_state == 'succeeded' and not has_automation_tags:
        reasons.append("Resource was provisioned without automation tags")

    return bool(reasons), reasons

def format_resource_output(resource: Dict[str, Any], reasons: List[str]) -> str:
    """
    Format resource details for user-friendly output.
    """
    tags = resource.get('tags', {}) or {}
    tags_str = '\n    '.join([f"{k} = {v}" for k, v in tags.items()]) if tags else "No tags"
    
    output = [
        f"📦 Resource: {resource['name']}",
        f"  Type: {resource['type']}",
        f"  Resource Group: {resource['resourceGroup']}",
        f"  Tags:",
        f"    {tags_str}",
        f"  Created Time: {resource.get('createdTime', 'Unknown')}",
        f"  Portal Creation Indicators:",
    ]
    
    for reason in reasons:
        output.append(f"    • {reason}")
    
    return '\n'.join(output)

def export_to_csv(portal_resources: List[tuple], filename: str, subscription_name: str):
    """
    Export portal-created resources to a CSV file.
    """
    try:
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header if file is empty
            if csvfile.tell() == 0:
                writer.writerow([
                    'Subscription',
                    'Resource Name',
                    'Resource Type',
                    'Resource Group',
                    'Tags',
                    'Created Time',
                    'Portal Creation Indicators'
                ])
            
            # Write data
            for resource, reasons in portal_resources:
                tags = resource.get('tags', {}) or {}
                tags_str = '; '.join([f"{k}={v}" for k, v in tags.items()]) if tags else "No tags"
                reasons_str = '; '.join(reasons)
                
                writer.writerow([
                    subscription_name,
                    resource['name'],
                    resource['type'],
                    resource['resourceGroup'],
                    tags_str,
                    resource.get('createdTime', 'Unknown'),
                    reasons_str
                ])
        
        print(f"\n✅ Results exported to {filename}")
    except Exception as e:
        print(f"\n❌ Error exporting to CSV: {str(e)}")

def main():
    """
    Main function to identify Azure portal-created resources.
    """
    args = parse_args()
    
    print("\n🔍 Azure Resource Analysis Tool")
    print("================================")
    
    check_az_cli()
    ensure_az_login()

    subscriptions = get_subscriptions()
    selected_subscriptions = select_subscription(subscriptions)

    print("\n⚙️  Analyzing resources...")
    
    total_resources = 0
    total_portal_created = 0
    
    # If output file specified, create/clear it
    if args.output:
        try:
            open(args.output, 'w').close()
        except Exception as e:
            print(f"\n❌ Error creating CSV file: {str(e)}")
            sys.exit(1)
    
    for subscription_id in selected_subscriptions:
        sub_name = next(name for id, name in subscriptions if id == subscription_id)
        print(f"\n📊 Analyzing subscription: {sub_name}")
        
        resources = fetch_resource_details(subscription_id)
        total_resources += len(resources)
        
        portal_created_resources = []
        for resource in resources:
            is_portal, reasons = is_portal_created(resource)
            if is_portal:
                portal_created_resources.append((resource, reasons))
        
        total_portal_created += len(portal_created_resources)
        
        print(f"\nFound {len(portal_created_resources)} portal-created resources "
              f"out of {len(resources)} total resources in this subscription.")
        
        if portal_created_resources:
            print("\n🔎 Portal-Created Resources:")
            for resource, reasons in portal_created_resources:
                print("\n" + "─" * 80)
                print(format_resource_output(resource, reasons))
            
            # Export to CSV if output file specified
            if args.output:
                export_to_csv(portal_created_resources, args.output, sub_name)
        else:
            print("\n✅ No portal-created resources found in this subscription.")
    
    print("\n📈 Summary")
    print("=========")
    print(f"Total resources analyzed: {total_resources}")
    print(f"Portal-created resources found: {total_portal_created}")
    if total_resources > 0:
        print(f"Percentage of portal-created resources: {(total_portal_created/total_resources)*100:.1f}%")

if __name__ == "__main__":
    main()
