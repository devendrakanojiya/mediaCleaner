async def _check_admin_rights(self, chat_id: int) -> bool:
    """Check if the user account has admin rights with delete permission."""
    try:
        me = await self.client.get_me()
        member = await self.client.get_chat_member(chat_id, me.id)
        
        # Check if creator
        if member.status == "creator":
            return True
        
        # Check if administrator
        if member.status == "administrator":
            # For user accounts as admin, check privileges
            if hasattr(member, 'privileges') and member.privileges:
                if hasattr(member.privileges, 'can_delete_messages'):
                    return bool(member.privileges.can_delete_messages)
                # If can_delete_messages is not accessible, assume True for admins
                return True
            # Default to True for admins if privileges can't be checked
            return True
        
        # If not creator or admin, try a different approach
        # Try to delete a non-existent message to check permissions
        try:
            await self.client.delete_messages(chat_id, [999999999])
        except Exception as del_error:
            error_str = str(del_error).lower()
            if "message_ids_empty" in error_str or "message to delete not found" in error_str:
                # This error means we have permission but message doesn't exist
                return True
            else:
                # Any other error means no permission
                return False
        
        return False
        
    except Exception as e:
        print(f"❌ Error checking admin rights: {e}")
        # Try the delete test as a fallback
        try:
            await self.client.delete_messages(chat_id, [999999999])
            return True
        except Exception as del_error:
            error_str = str(del_error).lower()
            if "message_ids_empty" in error_str or "message to delete not found" in error_str:
                return True
        return False
    










    