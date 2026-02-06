import re
import sys

def filter_dump(input_file, output_file):
    # Tables to remove (public schema)
    tables_to_remove = [
        'scenario',
        'scenario_act',
        'scenario_sequence',
        'play_logs',
        'session',
        'turn',
        'generation_logs'
    ]
    
    # Create regex patterns
    # Matches: CREATE TABLE public.tablename ... ;
    # Note: pg_dump usually puts CREATE TABLE on multiple lines.
    
    # We will process the file statefully to handle multi-line blocks
    
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        current_block_type = None
        skip_block = False
        buffer = []
        
        for line in f_in:
            # Check for start of a block we care about
            if line.startswith('CREATE TABLE public.'):
                table_name = line.split('public.')[1].split(' ')[0].strip('(').strip()
                if table_name in tables_to_remove:
                    skip_block = True
                    current_block_type = 'CREATE_TABLE'
                else:
                    skip_block = False
            
            elif line.startswith('COPY public.'):
                table_name = line.split('public.')[1].split(' ')[0].strip()
                if table_name in tables_to_remove:
                    skip_block = True
                    current_block_type = 'COPY'
                else:
                    skip_block = False

            elif line.startswith('ALTER TABLE ONLY public.'):
                table_name = line.split('public.')[1].split(' ')[0].strip()
                if table_name in tables_to_remove:
                    skip_block = True
                    current_block_type = 'ALTER_TABLE'
                else:
                    skip_block = False
            
            # Write line if we are not skipping
            if not skip_block:
                f_out.write(line)
            
            # Check for end of block to reset state
            if skip_block:
                if current_block_type == 'CREATE_TABLE' and line.strip().endswith(';'):
                    skip_block = False
                    current_block_type = None
                elif current_block_type == 'ALTER_TABLE' and line.strip().endswith(';'):
                    skip_block = False
                    current_block_type = None
                elif current_block_type == 'COPY' and line.strip() == '\.':
                    skip_block = False
                    current_block_type = None

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python filter_dump.py <input_dump> <output_dump>")
        sys.exit(1)
    
    filter_dump(sys.argv[1], sys.argv[2])
