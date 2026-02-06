import sys
import re

def get_target_db(table_name):
    # Rule DB Tables
    if table_name in ['users', 'session', 'user_sessions']:
        return 'rule'
    # Play DB Tables
    if table_name in ['play_logs', 'turn', 'generation_logs']:
        return 'play'
    # Graph DB Tables (Scenario + State + Default)
    return 'graph'

def split_dump(input_file, out_graph, out_play, out_rule):
    f_graph = open(out_graph, 'w', encoding='utf-8')
    f_play = open(out_play, 'w', encoding='utf-8')
    f_rule = open(out_rule, 'w', encoding='utf-8')
    
    files = {'graph': f_graph, 'play': f_play, 'rule': f_rule}
    
    current_target = 'graph' # Default
    
    with open(input_file, 'r', encoding='utf-8') as f_in:
        for line in f_in:
            lower_line = line.lower()
            
            # Table detection
            if line.startswith('CREATE TABLE public.'):
                table_name = line.split('public.')[1].split(' ')[0].strip('(').strip()
                current_target = get_target_db(table_name)
            elif line.startswith('COPY public.'):
                table_name = line.split('public.')[1].split(' ')[0].strip()
                current_target = get_target_db(table_name)
            elif line.startswith('ALTER TABLE ONLY public.'):
                table_name = line.split('public.')[1].split(' ')[0].strip()
                current_target = get_target_db(table_name)
            elif line.startswith('CREATE INDEX') and ' ON public.' in line:
                # CREATE INDEX idx ON public.tablename ...
                try:
                    table_name = line.split(' ON public.')[1].split(' ')[0].strip().split('(')[0]
                    current_target = get_target_db(table_name)
                except:
                    pass # Keep previous target if parse fails

            # Global / Common Objects
            is_global = False
            
            # Sequences: Write to ALL to avoid dependency issues (simplification)
            if line.startswith('CREATE SEQUENCE') or line.startswith('ALTER SEQUENCE') or line.startswith('SELECT pg_catalog.setval'):
                is_global = True
                
            # Types/Domains/Functions: Write to ALL (simplification)
            if line.startswith('CREATE TYPE') or line.startswith('CREATE DOMAIN') or line.startswith('CREATE FUNCTION'):
                is_global = True

            # Configuration & Comments
            if line.startswith('SET ') or line.startswith('SELECT ') or line.startswith('--') or line.startswith('\\.'):
                is_global = True
            
            # Extensions
            if line.startswith('CREATE EXTENSION'):
                if 'vector' in line:
                    files['play'].write(line)
                elif 'age' in line:
                    files['graph'].write(line)
                else:
                    for f in files.values(): f.write(line)
                continue
            
            if line.startswith('COMMENT ON EXTENSION'):
                 for f in files.values(): f.write(line)
                 continue

            if is_global:
                for f in files.values(): f.write(line)
            else:
                files[current_target].write(line)

    f_graph.close()
    f_play.close()
    f_rule.close()

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python split_dump.py <input> <out_graph> <out_play> <out_rule>")
        sys.exit(1)
    
    split_dump(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
