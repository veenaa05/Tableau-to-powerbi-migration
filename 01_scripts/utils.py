
def generate_incremental_aliases(num_aliases):
    aliases = []
    for i in range(num_aliases):
        alias = ''
        n = i
        while n >= 0:
            alias = chr(n % 26 + ord('a')) + alias
            n = n // 26 - 1  # Move to the next "digit"
        aliases.append(alias)
    return aliases

def generate_table_aliases(data):
    unique_tables = set(value['table'] for value in data.values())
    num_tables = len(unique_tables)
    aliases = generate_incremental_aliases(num_tables)
    
    table_alias_mapping = {}
    for table, alias in zip(unique_tables, aliases):
        table_alias_mapping[table] = alias
    
    return table_alias_mapping

